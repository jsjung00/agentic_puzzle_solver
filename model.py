'''
Contains Plan Re-Planner
'''
from openai import OpenAI
from dotenv import load_dotenv
import json 
import pdb 
from collections import defaultdict
import math 
from constants import incorrect_json_str, plan_generator_system_prompt, replan_generator_system_prompt

load_dotenv()
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


        
    






