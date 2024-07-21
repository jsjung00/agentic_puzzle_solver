'''
Contains Plan Re-Planner
'''
from openai import OpenAI
from dotenv import load_dotenv
import json 
import pdb 
from collections import defaultdict
import math 
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

class Replanner:
    # generates one plan that is validated as correct
    def __init__(self, all_words: list[str]) -> None:
        self.all_words = all_words
        self.jury_failed_groups = [] # list of voted failed {category: [group_words] } groups  
        self.failed_groups = [] # list of env failed {category: [group_words] }
        self.jury = Jury()
    
    def update_jury_failed_groups(self, plan, is_valid_arr):
        for i in range(0, len(is_valid_arr)):
            if not is_valid_arr[i]:
                self.jury_failed_groups.append(plan[i])
        return 



    def generate_plan(self):
        '''
        Generates a list (denoted plan) of four [{category: [group_words] }] using all words
            Replans if 2,3 generated categories makes sense, returns plan if all make sense,
            returns None if <= 1 generated categories make sense
        '''
        client = OpenAI()
        system_prompt = f'''You are a smart NYT Connections puzzle solver. You are given a set of words and\
            from those words you will generate groups of four words, where each group has some category theme and\
                  the groups have no overlapping words.
        
        Return the groups as JSON object with a single key 'groups' whose value is an array of objects. Each object should have a single key-value pair, where the key is the category theme and the value is an array of 4 words in the group.
        word_set = ['CAMPAIGN', 'CANVASS', 'CLAMP', 'COMPOSITION', 'FABRIC', 'FILE', 'LEVEL', 'LOG', 'MAKEUP', 'MAX', 'MOD', 'ORGANIZE', 'SAW', 'STRUCTURE', 'STUMP', 'TAN']
        Return:
        {{"groups": [
            {{
                "WAYS TO SUPPORT A CANDIDATE": ["CAMPAIGN", "CANVASS", "ORGANIZE", "STUMP"]
            }},
            {{
                "CONSTITUTION": ["COMPOSITION", "FABRIC", "MAKEUP", "STRUCTURE"]
            }},
            {{
                "CARPENTRY TOOLS": ["CLAMP", "FILE", "LEVEL", "SAW"]
            }},
            {{
                "MATH ABBREVIATIONS": ["LOG", "MAX", "MOD", "TAN"]
            }}
        ]}}
        Always return valid JSON in this format.
        '''
        
        user_prompt = f"Set of words to generate groups of 4 from: {self.all_words}"
        history = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=history,
            response_format={ "type": "json_object" },
        )
        response_msg = response.choices[0].message.content
        response_json = json.loads(response_msg)
        if isinstance(response_json, dict) and 'groups' in list(response_json.keys()):
            plan = response_json['groups']
        else:
            raise ValueError(f"GPT generated the wrong JSON output. {response_msg}")
        
        # evaluate the generated groups
        is_valid_arr = self.jury.get_verdict(plan)
        num_valid = sum(map(int, is_valid_arr))

        if num_valid <= 1:
            self.update_jury_failed_groups(plan, is_valid_arr)
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
        client = OpenAI()
        system_prompt = f'''You are a smart NYT Connections puzzle solver. You are given a set of words and\
            from those words you will generate groups of four words, where each group has some category theme and\
                  the groups have no overlapping words.
        
        Return the groups as JSON object with a single key 'groups' whose value is an array of objects. Each object should have a single key-value pair, where the key is the category theme and the value is an array of 4 words in the group.
        word_set = ['CAMPAIGN', 'CANVASS', 'CLAMP', 'COMPOSITION', 'FABRIC', 'FILE', 'LEVEL', 'LOG', 'MAKEUP', 'MAX', 'MOD', 'ORGANIZE', 'SAW', 'STRUCTURE', 'STUMP', 'TAN']
        Return:
        {{"groups": [
            {{
                "WAYS TO SUPPORT A CANDIDATE": ["CAMPAIGN", "CANVASS", "ORGANIZE", "STUMP"]
            }},
            {{
                "CONSTITUTION": ["COMPOSITION", "FABRIC", "MAKEUP", "STRUCTURE"]
            }},
            {{
                "CARPENTRY TOOLS": ["CLAMP", "FILE", "LEVEL", "SAW"]
            }},
            {{
                "MATH ABBREVIATIONS": ["LOG", "MAX", "MOD", "TAN"]
            }}
        ]}}
        Always return valid JSON in this format.
        '''
        
        user_prompt = f"Set of words to generate groups of four from: {remaining_words}"
        history = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=history,
            response_format={ "type": "json_object" },
        )
        response_msg = response.choices[0].message.content
        response_json = json.loads(response_msg)
        if isinstance(response_json, dict) and 'groups' in list(response_json.keys()):
            plan = response_json['groups']
        else:
            raise ValueError(f"GPT generated the wrong JSON output. {response_msg}")
        
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
        


        
    






