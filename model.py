'''
Contains Plan Re-Planner
'''
from openai import OpenAI
from dotenv import load_dotenv
import json 
import pdb 
from collections import defaultdict, Counter
import math 
import numpy as np 
from constants import incorrect_json_str, plan_generator_system_prompt, replan_generator_system_prompt
import copy 
import agentops
import os

load_dotenv()
agentops.init(os.environ['AGENT_OPS_KEY'])



class Orchestrator:
    '''
    Generates the responses from the agents after debate, verifies and does feedback, ranks the outputs, generates a list of groups to try
        and it executes action 
    '''
    def __init__(self, remaining_words, groups_correct:int, failed_groups: list[str]):
        self.remaining_words = remaining_words
        self.groups_correct = groups_correct
        self.debater = Debate(self.remaining_words, num_rounds=2, num_agents=3)
        self.failed_groups = failed_groups

        self.ranked_solutions = [] # list of dicts where key is rank and value is group 
        self.used_words = set() #keeps track of words that have been succesfully submitted 
        self.ranked_groups = []
    
    def ret_ranked_groups(self):
        '''
        Returns a sorted list of groups, sorted by the groups with most votes across solutions, ties broken by rank 
        '''
        # TODO: change the hash to tuple, alphabetically sorted
        # get number votes of each group
        num_votes = defaultdict(int)
        
        ranks = defaultdict(list) # index is list of words converted to string using '#'.join
        for i in range(0, len(self.ranked_solutions)):
            sol = self.ranked_solutions[i]
            for rank, group_words in sol.items():
                group_key = tuple(sorted(group_words)) #key is tuple of group set (alpha sorted for order invariance)
                ranks[group_key].append(int(rank))
                num_votes[group_key] += 1

        # get average rank of each group   
        avg_ranks = {} #key: group_hash, val: avg_rank
        for group_hash, ranks in ranks.items():
            avg_ranks[group_hash] = float(np.mean(ranks))


        group_items = [] #(group_hash, num_votes, avg_rank)
        for group_hash in num_votes.keys():
            group_list = list(group_hash)
            votes = num_votes[group_hash]
            avg_rank = avg_ranks[group_hash]

            group_items.append((group_list, votes, avg_rank))

        sorted_group_items = sorted(group_items, key=lambda x: (-x[1], x[2])) #sort first by num votes, then avg_rank
        self.ranked_groups = [tup[0] for tup in sorted_group_items]
        return self.ranked_groups

    def get_next_group(self):
        # return first group that does not use already used words 
        for group in self.ranked_groups:
            if len(set(group) & self.used_words) == 0:
                return group 
        
        raise ValueError("No groups that don't include some of the used words")
        return 

    def update_used_words(self, words: list[str]):
        for word in words:
            self.used_words.add(word)
        
        return 

    def run_round(self):
        '''
        Executes a round. Returns (list of successful groups, failed group if exists)
        '''
        successful_groups = [] 
        all_sols_valid = False 
        self.debater.update_failed_groups(self.failed_groups)
        list_sols = self.debater.driver()

        # continues to generate responses until satisfies all the rules 
        while (all_sols_valid == False):
            verifier = Verifier(list_sols, self.remaining_words)
            are_sols_valid = verifier.ret_solutions_valid()
            if not all(are_sols_valid):
                # update the solutions for the ones that failed
                for i in range(0, len(are_sols_valid)):
                    if not are_sols_valid[i]:
                        context = self.debater.agent_contexts[i].copy()
                        if len(self.failed_groups):
                            context.append({'user': f"Also use the fact that the incorrect groups of words are {self.failed_groups}"})
                        correction_prompt = verifier.correction_prompts[i]
    
                        model = Model('gpt-4o',history=context)
                        text_response = model.forward(correction_prompt)
                        list_sols[i] = self.debater.get_json_puzzle_solution(text_response)
            
            all_sols_valid = all(are_sols_valid)            
        
        ranker = Ranker(list_sols)
        ranked_sols = ranker.rank_solutions()
        self.ranked_solutions = ranked_sols

        ranked_groups = self.ret_ranked_groups() #TODO: FIX: SHOULD BE MORE THAN 4
        self.ranked_groups = ranked_groups

        result = True
        while(result):
            if self.groups_correct >= 4: break 

            next_group = self.get_next_group()
            result = self.execute_group(next_group)
            if result:
                successful_groups.append(next_group)
                self.update_used_words(next_group)
                self.groups_correct += 1
            
            self.ranked_groups.remove(next_group)

        if self.groups_correct >= 4:
            return successful_groups, None 
    
        return successful_groups, next_group 


    def execute_group(self, group):
        # Returns boolean if group was successful
        def get_result(group_words):
            print(group_words)
            user_input = input("Was it succeed, Y or N: ")
            return True if user_input == "Y" or user_input == "y" else False 
        
        return get_result(group)






class Model:
    def __init__(self, model_name:str, base_prompt='You are a helpful assistant.', history=None):
        self.model_name = model_name
        if 'gpt' in model_name:
            self.client = OpenAI()
        assert 'gpt' in model_name

        if history:
            self.history = history 
        else:
            self.history = [{"role": "system", "content": base_prompt}]


    def forward(self, prompt=None, json_mode=False):
        '''
        Calls model and returns output 
        '''
        if prompt:
            self.history.append({"role": "user", "content": prompt})
        
        if json_mode:
            completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.history,
            response_format={ "type": "json_object" })
        else:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history)
        content = completion.choices[0].message.content
        self.history.append({"role": "assistant", "content": content})

        return content 

class Ranker:
    '''
    Takes in a list of solutions and returns a list of solution where each solution has the groups ranked
    '''
    def __init__(self, list_solutions):
        '''
        list_solutions: List[Dict], Dict is {theme: group_words_list}
        '''
        system_prompt = "You are an expert NYT Connections solver. You will be given some candidate solution of categories and their groups of words. Please rank the groups by your confidence on the correctness of the group, with 1 being the most confident."
        self.list_solutions = list_solutions
        self.model = Model("gpt-4o", system_prompt)
    
    def rank_solution(self, solution):
        '''
        Ranks solution and returns a string with ranked groups in content 

        solution: Dict (key: group theme, val: List[str])
        '''
        prompt = f"Solution: {solution}"
        response = self.model.forward(prompt)

        return response 

    def shape_json(self):
        '''
        Takes string from rank_solution and returns Dict where key is the rank (confidence rank, 1 highest) and value is a (key: group theme, group_words: List[str])
        '''
        prompt = f'''Please convert your previous response with the ranked groups into a json format.
        You are to return a JSON object where the key is the rank [1-4] and the value is the corresponding group of words.
        
        Example: {{1: ["CAMPAIGN", "CANVASS", "ORGANIZE", "STUMP"], 2: ["COMPOSITION", "FABRIC", "MAKEUP", "STRUCTURE"], 3:["CLAMP", "FILE", "LEVEL", "SAW"], 4:["LOG", "MAX", "MOD", "TAN"]}}'''
        json_response = self.model.forward(prompt, json_mode=True)
        ranked_solution = json.loads(json_response)
        return ranked_solution 


    def rank_solutions(self):
        '''
        Returns a list of dictionaries where the key is the confidence rank and the val is the group of words 
        '''
        ranked_solutions = []
        for i in range(0, len(self.list_solutions)):
            sol = self.list_solutions[i]
            _ = self.rank_solution(sol)
            ranked_solutions.append(self.shape_json())

        return ranked_solutions


class Verifier:
    '''
    Takes in a list of dictionaries which each holds groups of size 4 and their their themes
        and verifies that they satisfy the rules.
    '''
    def __init__(self, list_solutions, available_words: list[str]):
        '''
        list_solutions: List[Dict], Dict is {theme: group_words_list}
        available_words: list[str] words to create groups with
        '''
        self.list_solutions = list_solutions 
        self.solutions_valid = [] #list of booleans corresponding to whether the solution is valid
        self.correction_prompts = ['' for _ in range(len(self.list_solutions))]
        self.available_words = available_words

    def check_disjoint_sets(self, list_of_sets):
        for i in range(len(list_of_sets)):
            for j in range(i + 1, len(list_of_sets)):
                if list_of_sets[i] & list_of_sets[j]:  # Check for intersection
                    return False
        return True

    def is_solution_valid(self, solution):
        '''
        Returns boolean if solution (i.e all groups in dict) are valid, correction prompt string (can be empty if correct)
        
        solution: (Dict)
        '''
        # check number of groups
        if len(list(solution.values())) != len(self.available_words) // 4:
            print("Incorrect number of groups")
            return False, f"The solution you returned has an incorrect number of groups. The remaining words {self.available_words} has {len(self.available_words)} words and so should have {len(self.available_words)//4} groups. Please reflect on this and create a new solution."
        # check number of words 
        for group in list(solution.values()):
            if len(group) != 4:
                print("Incorrect number of words in a group")
                return False, f"The solution must return groups of four words. Your solution contains a group {group} with {len(group)} words. Please reflect and create a new solution."
        #check if words come from available words
        for group in list(solution.values()):
            for word in group:
                if word not in self.available_words:
                    print("Incorrect words chosen")
                    return False, f"The solution must return groups of four words that come from the set of available words {self.available_words}. Your solution contains a group {group} with a word that is not in the set of available words. Please reflect and create a new solution."
        #check if no groups share a word
        list_group_sets = [set(group) for group in list(solution.values())]
        all_disjoint = self.check_disjoint_sets(list_group_sets)
        if not all_disjoint:
            print(f"Groups {list_group_sets} are not disjoint")
            return False, f"The solution must use the available words and partition them into groups of four words that do not share a word with any other group. Your solution has groups that share words. Please reflect on this and create a new solution."

        return True, ""
        
    def ret_solutions_valid(self):
        '''
        Returns a list of booleans on whether agent solution is correct 
            Also updates self.correction_prompts
        '''
        for i in range(0, len(self.list_solutions)):
            sol = self.list_solutions[i]
            is_valid, prompt_str = self.is_solution_valid(sol)
            self.correction_prompts[i] = prompt_str
            self.solutions_valid.append(is_valid)

        return self.solutions_valid
    










'''
Some notes from the debate paper: https://openreview.net/pdf?id=zj7YuTE4t8#page=12&zoom=100,409,81
    - Add a longer debate prompt
    - Use number of debate rounds 3 or larger
    - Use up to 5 debate agents (start with 3)
    - Add the other people's reasoning to the history 
'''

class Debate:
    '''
    Conducts a debate and returns a list of dictionaries which each hold groups of size 4 and their themes based on the current
        available words
    '''
    def __init__(self, available_words: list[str], num_rounds:int, num_agents:int):
        self.available_words = available_words
        self.num_rounds = num_rounds
        self.num_agents = num_agents
        self.client = OpenAI()
        self.agent_contexts = []
        self.failed_groups = [] #list of group words that failed

    def update_failed_groups(self, failed_groups):
        self.failed_groups = failed_groups

    def construct_assistant_msg(self, completion):
        content = completion.choices[0].message.content
        return {"role": "assistant", "content": content}
    
    def generate_answer(self, answer_context):
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=answer_context)
        return completion

    def construct_message(self, agent_contexts_other, question, idx):
        '''
        Creates a message to reflect on other agents explanation and answer. 
            If no other agents, then creates a message for self reflection
        '''
        if len(agent_contexts_other) == 0:
            return {"role": "user", "content": """Please double check if your solution is correct. Look through the group of words created and their corresponding group themes and see if the group words match the theme.
                    Put your final solution with the groups and themes you have created in the form **group name**: [word_one, word_two, word_three, word_four"""}
        
        prefix_string = "These are the solutions and solution explanations to the Connections puzzle from other agents: "
        for agent_context in agent_contexts_other:
            #TODO: need to use 4o-mini to extract solution and summarize reasoning from word spillage and format. 
            agent_response = agent_context[idx]["content"]
            response = f"\n\n One agent solution: ```{agent_response}```"
            prefix_string += response 
        
        prefix_string += """\n\n Using the reasoning from other agents as additional advice, can you give an updated answer? Examine your solution and that of other agents step by step. Put your solution with the groups and themes you have created in the form **group name**: [word_one, word_two, word_three, word_four"""
        return {"role": "user", "content": prefix_string}
                    

    def ret_agent_contexts(self): 
        if len(self.available_words) == 16:
            system_prompt = """You are a NYT Connections solver. As a reminder,
            The NYT Connections game is a word puzzle where players are given a grid of 16 words and must categorize them into four groups of four words each.
            The main rules include: 
            1. **Grid Structure**: The game presents 16 words arranged in a 4x4 grid.
            2. **Grouping**: Players need to identify four distinct groups of four words that share a common theme or category. Each group must consist of exactly four words.
            3. **Word Usage**: Each word can only belong to one group. 
            4. **Winning the Game**: The goal is to correctly group all 16 words into the four categories. 
            
            You will be given the list of remaining words on the grid. You may also be given a list of groups of four words
            that have failed and are incorrect. Your job is to use this information, follow the rules, and create
            groups to solve the game.
            """
        else:
            system_prompt = """You are an expert NYT Connections solver. You will be given the list of remaining words on the grid. You may also be given a list of groups of four words
            that have been tried and are incorrect. Your job is to use this information, follow the rules, and create
            groups from the list of remaining words to solve the game.
            """

        if self.failed_groups:
            question = (
            f"The available words are {self.available_words}. The groups of words that are incorrect are {self.failed_groups}."
            "Can you solve the NYT "
            "Connections puzzle by creating groups of four words that share a common "
            "theme or category. Deliberate and then explain the reasoning behind the "
            "groups you have created, putting your answer in the form "
            "**group name**: [word_one, word_two, word_three, word_four]"
            )
        else:
            question = (
            f"The available words are {self.available_words}. Can you solve the NYT "
            "Connections puzzle by creating groups of four words that share a common "
            "theme or category. Deliberate and then explain the reasoning behind the "
            "groups you have created, putting your answer in the form "
            "**group name**: [word_one, word_two, word_three, word_four]"
        )        
  
        agent_contexts = [[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}] for _ in range(self.num_agents)]

        for round in range(self.num_rounds):
            for i, agent_context in enumerate(agent_contexts):
                if round > 0:
                    agent_contexts_other = agent_contexts[:i] + agent_contexts[i+1:]
                    message = self.construct_message(agent_contexts_other, question, 2*round)
                    agent_context.append(message)
                
                completion = self.generate_answer(agent_context)
                assistant_msg = self.construct_assistant_msg(completion)
                agent_context.append(assistant_msg)
                #TODO: send generation content to backend to show on webapp
                #print(f'Round {round + 1} Agent {i + 1}')
                print(f'Round {round + 1} Agent {i + 1}: {assistant_msg['content']}')

        return agent_contexts

    def get_json_puzzle_solution(self, response: str):
        system_prompt = (
            "You are a helpful agent. You will be given a response by another GPT agent that "
            "consists of a solution to the NYT Connections puzzle and their explanation for it. "
            "Please extract the solution, which are the lists of words in the group and their category theme, "
            "and return a JSON object where the keys represent the category themes and the values represent the corresponding list of four words that fit the category.\n"
            "For example:\n"
            "{\n"
            '    "WAYS TO SUPPORT A CANDIDATE": ["CAMPAIGN", "CANVASS", "ORGANIZE", "STUMP"],\n'
            '    "CONSTITUTION": ["COMPOSITION", "FABRIC", "MAKEUP", "STRUCTURE"],\n'
            '    "CARPENTRY TOOLS": ["CLAMP", "FILE", "LEVEL", "SAW"],\n'
            '    "MATH ABBREVIATIONS": ["LOG", "MAX", "MOD", "TAN"]\n'
            "}"
        )
        user_prompt = f"GPT response: {response}"
        history = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=history,
            response_format={ "type": "json_object" },
        )
        response_msg = response.choices[0].message.content
        response = json.loads(response_msg)
        return response 

    
    def driver(self):
        '''
        Returns the list of dictionaries representing agent solutions; each dict has key: group_theme and val: list of group words
        '''
        agent_contexts = self.ret_agent_contexts()
        self.agent_contexts = agent_contexts
        list_solutions = [] # contains solutions represented as dicts with key: group theme and val: list of group words
        for i in range(0, len(agent_contexts)):
            last_response = agent_contexts[i][-1]['content']
            response_dict = self.get_json_puzzle_solution(last_response)
            list_solutions.append(response_dict)
        
        return list_solutions



        


#TODO: use different model types 
class Jury:
    def __init__(self, num_judges=3):
        self.num_judges = num_judges

    def judge(self, plan):
        '''
        Given a plan, return a List of Bools on whether the corresponding group makes sense
        plan: List[{category: group words}]
        '''
        client = OpenAI()
        #TODO: add some incontext examples
        system_prompt = (
            "You are a judge evaluating a solution to the NYT Connections game, a game that requires the player "
            "to create four groups consisting of four words where each group has some categorical theme.\n"
            "You will be given a solution which consists of a list of dictionaries, each dictionary contains one key "
            "representing the category theme and one value representing the list of words in the group.\n"
            "You are to return a JSON object with a single key 'valid_bools' and single list of booleans corresponding "
            "to whether the corresponding group in the solution array makes sense.\n\n"
        )
        user_prompt = f"Solution to verify: {plan}"
        history = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=history,
            response_format={ "type": "json_object" },
        )
        response_msg = response.choices[0].message.content
        #print(f'Plan {plan}')
        #print(f"Judge output: {response_msg}")

        response = json.loads(response_msg)
        if isinstance(response, dict) and "valid_bools" in response:
            return response['valid_bools']

        raise ValueError(f"GPT returned the wrong json for judge: {response_msg}")

    def ret_majority_bool(self, list_bools):
        num_true = 0
        for bool in list_bools:
            num_true += int(bool)
        
        return num_true >= math.ceil(len(list_bools)/2)

    def group_votes(self, plan):
        '''
        Returns a dictionary with key: index of the group element
            and val as the list of booleans representing the judges votes
        '''
        total_votes = defaultdict(list) #key: index   val: [bools]

        for _ in range(self.num_judges):
            valid_bools = self.judge(plan) # list of bools 
            for i in range(0, len(valid_bools)):
                total_votes[i].append(valid_bools[i])
        return total_votes

    def get_final_vote(self, total_votes_dict):
        '''
        Returns a dictionary with key: index of the group element
            and val as is_valid bool 
        '''
        final_vote = {}
        for key, value in total_votes_dict.items():
            final_vote[key] = self.ret_majority_bool(value) 
        return final_vote

    def get_verdict(self, plan):
        '''
        Returns a list of is_valid bool coresponding to whether the plan element (i.e group) is valid
        '''
        jury_votes = self.group_votes(plan)
        vote_dict = self.get_final_vote(jury_votes)
        is_valid = []
        for i in range(0, len(list(vote_dict.items()))):
            is_valid.append(vote_dict[i])

        return is_valid


class GPT:
    def __init__(self, user_prompt, system_prompt, failed_plans, model_type='gpt-4o'):
        self.user_prompt = user_prompt
        self.system_prompt = system_prompt
        self.failed_plans = failed_plans
        if self.failed_plans:
            self.history = [
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": f'Previous failed list of groups: """{failed_plans}"""'},
                    {"role": "user", "content": user_prompt}
            ]
        else:
            self.history = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
            ]
        self.client = OpenAI()
        self.model_type = model_type
    
    def return_json(self):
        response = self.client.chat.completions.create(
            model=self.model_type,
            messages=self.history,
            response_format={ "type": "json_object" },
        )
        response_msg = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": response_msg})
        response_json = json.loads(response_msg)
        return response_json
    
    def check_disjoint_sets(self, list_of_sets):
        for i in range(len(list_of_sets)):
            for j in range(i + 1, len(list_of_sets)):
                if list_of_sets[i] & list_of_sets[j]:  # Check for intersection
                    return False
        return True

    
    def check_valid_json(self, output, board_words):
        # output: (dict) Has key: 'groups'
        # Checks if the loaded json is valid. Returns boolean
        if isinstance(output, dict) and 'groups' in list(output.keys()):
            plan = output['groups']
        else:
            print("Output not in json format with key groups")
            return False 
        
        list_groups = [] # list of all the group words as sets
        # check if created right number of groups
        if len(board_words) // 4 != len(plan):
            print("Created wrong number of groups.")
            return False 

        # check if each group has four words 
        for i in range(len(plan)):
            category, group_words = list(plan[i].items())[0]
            list_groups.append(set(group_words))
            if len(group_words) != 4:
                print("Not all groups have length 4")
                return False 
            
            # check if group words come from board words
            for word in group_words:
                if word not in board_words: 
                    print("Group word not from board words")
                    return False 

        
        all_disjoint = self.check_disjoint_sets(list_groups)
        if not all_disjoint:
            print("Groups aren't disjoint")
            return False  
        return True  

    def forward(self, board_words):
        '''
        Generates responses until you get a valid response. Returns plan which is a list of [{category: [group_words]]
        '''
        is_valid = False
        while (not is_valid):
            output = self.return_json()
            is_valid = self.check_valid_json(output, board_words)

            if not is_valid:
                self.history.append({"role": "user", "content": incorrect_json_str})
                print(f"GPT returned an invalid response.\n")
                print()
            
        return output['groups'] 


class Replanner:
    # generates one plan that is validated as correct
    def __init__(self, all_words: list[str]) -> None:
        self.all_words = all_words #all words remaining on the board 
        self.jury_failed_groups = [] # list of voted failed {category: [group_words] } groups  
        self.failed_groups = [] # list of env failed {category: [group_words] }
        self.failed_plans = [] #list of failed plans [{category: [group_words] }]
        self.jury = Jury()
    
    def update_jury_failed_groups(self, plan, is_valid_arr):
        for i in range(0, len(is_valid_arr)):
            if not is_valid_arr[i]:
                self.jury_failed_groups.append(plan[i])
        return 
    
    def update_failed_group(self, group_dict):
        # adds {category: [group_words] } to the history 
        self.failed_groups.append(group_dict)
    
    def update_all_words(self, remaining_words):
        self.all_words = remaining_words

    def update_failed_plans(self, plan):
        self.failed_plans.append(plan)



    def generate_plan(self):
        '''
        Generates a list (denoted plan) of [{category: [group_words] }] using all words remaining on board
            Replans if 2,3 generated categories makes sense, returns plan if all make sense,
            returns None if <= 1 generated categories make sense
        '''
        user_prompt = f'Use these set of words to generate groups of four from: """{self.all_words}"""'
        
        gpt_gen = GPT(user_prompt, plan_generator_system_prompt, self.failed_plans)
        plan = gpt_gen.forward(self.all_words)
        print(f"Generated Plan: {plan}\n")
        
        # evaluate the generated groups
        is_valid_arr = self.jury.get_verdict(plan)
        num_valid = sum(map(int, is_valid_arr))
        print(f"Jury verdict: {is_valid_arr}")

        if num_valid <= 1:
            self.update_jury_failed_groups(plan, is_valid_arr)
            self.update_failed_plans(plan)
            return None  
        elif num_valid < 4:
            used_words = set()
            new_plan = [] # contains {category: [group_words]}
            for i in range(0, len(is_valid_arr)):
                if is_valid_arr[i]:
                    group_words = set(list(plan[i].values())[0])
                    used_words.update(group_words)
                    new_plan.append(plan[i])
            remaining_words = list(set(self.all_words) - used_words)
            regen_result = self.regenerate_plan(remaining_words)

            # check if regeneration of the remaining words fails 
            if regen_result is None:
                # TODO: if regen fails, we might assume the first "correct" ones are false
                self.update_jury_failed_groups(plan, is_valid_arr)
                self.update_failed_plans(plan)
                return None

            new_plan.extend(regen_result)
            return new_plan
        else:
            return plan 
        
    #TODO: regenerate multiple plans using different agents and check to see if any of them succeed
    def regenerate_plan(self, remaining_words):
        '''
        Generates a list (denoted plan) of four [{category: [group_words] }] using remaining words
            Returns None if not all of the groups make sense, otherwise returns the plan which is list [{category: [group_words] }] of remaining words
        '''
        user_prompt = f'Set of words to generate groups of four from: """{remaining_words}"""'
        gpt_gen = GPT(user_prompt, replan_generator_system_prompt, self.failed_plans)
        plan = gpt_gen.forward(remaining_words)
        print(f"Words: {remaining_words}\n Regenerated Plan: {plan}\n")
      
        # evaluate the generated groups
        is_valid_arr = self.jury.get_verdict(plan)
        num_valid = sum(map(int, is_valid_arr))

        if num_valid != len(is_valid_arr):
            return None 

        return plan 
       
    def driver(self):
        generated_result = None
        while(generated_result is None):
            print("Generating a new plan")
            generated_result = self.generate_plan()
        
        # try out the given plan 
        # TODO: rank the elements in the given plan or use the votes by the jury to decide which one to try out first
        return generated_result


        
    






