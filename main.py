from openai import OpenAI
from dotenv import load_dotenv
import json 
import pdb 
from model import Replanner

'''
I want to take a list of words, generate some initial plan, and then be able to evaluate the plan. 
I want to ask it to self-reflect
'''
load_dotenv()

def generate(words, num_to_predict, failed_words, history, self_reflection):
    '''
    words: (List[str]) List of words to generate groups from 
    failed_words:[] List of words that did not work
    self_reflection: (bool) If should use self reflection in the output 

    Return groups (List of JSONs), return history
    '''
    
    if self_reflection:
        raise NotImplementedError()
    else:
        client = OpenAI()
        system_prompt = f'''I want you to be a smart, well reasoned NYT connections textual puzzle solver. You will be given a set of words\
            and a number of groups (represented by variable num_of_groups) to generate; using those set of words, you will generate num_of_groups\
            many groups consisting of 4 words, where the groups must not contain any overlapping words. You may also be given feedback on previous outputs that did not work; use that feedback to your advantage.
        
        Before returning anything, please think through which groups you have more confidence in and then sort the generated groups by your confidence.
        You should return the groups as a JSON object with a single key "groups" whose value is an array of objects. Each object should have a single key-value pair, where the key is the category/group theme and the value is an array of 4 words.
        The order in the list should have your most confident group go first. For example:

        num_of_groups = 2
        word_set = ['BATTERY', 'BURST', 'CHARGE', 'DAD', 'EFFORT', 'FLUID', 'GRACEFUL', 'JUICE', 'LABOR', 'MAINSTREAM', 'NATURAL', 'POWER', 'SMOOTH', 'SODA', 'SWEAT', 'WORK']
        Return:
        {{
            "groups": [
                {{
                    "EFFORTLESS": ["FLUID", "GRACEFUL", "NATURAL", "SMOOTH"]
                }},
                {{
                    "EXERTION": ["EFFORT", "LABOR", "SWEAT", "WORK"]
                }}
            ]
        }}

        num_of_groups = 1
        word_set = ['COFFEE', 'DIESEL', 'PERIODIC', 'PLUS', 'POOL', 'PREMIUM', 'REGULAR', 'WATER']
        Return:
        {{
            "groups": [
                {{
                    "GAS PUMP OPTIONS": ["DIESEL", "PLUS", "PREMIUM", "REGULAR"]
                }}
            ]
        }}

        Always return valid JSON in this format.
        '''
        
        if len(failed_words) > 0:
            user_prompt=f"""Your predicted group {failed_words} was incorrect. Please try another output.
            num_of_groups={num_to_predict} word_set={words}
            """ 
        else:
            user_prompt = f"""num_of_groups={num_to_predict} word_set={words}"""
        if history is None:
            history = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        else:
            history.append({"role": "user", "content": user_prompt}) 

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=history,
            response_format={ "type": "json_object" },
        )
        response_msg = response.choices[0].message.content
        history.append({"role": "assistant", "content": response_msg})

        print(f"User input: {user_prompt}\n")
        return response_msg, history 
    

def predict_groups(words, groups_correct, failed_words=[], history=None, self_reflection=False):
    '''
    words: List[str]
    groups_correct: int Number groups correct so far
    return List[Dict[str: List[str]]] each object is {category_theme: [words]}
    '''

    response_msg, history = generate(words, 4, failed_words, history, self_reflection)
    response_json = json.loads(response_msg)
    if isinstance(response_json, dict) and 'groups' in list(response_json.keys()):
        response_json = response_json['groups']
    print(f"GPT output: {response_json}\n")
    
    if not isinstance(response_json, list):
        raise TypeError("GPT returned wrong json type")
    return response_json, history



class Engine:
    def __init__(self, all_words: list[str]):
        self.groups_correct = 0
        self.num_mistakes = 0
        self.remaining_words = all_words
        self.planner = Replanner(self.remaining_words)
    
    def execute_plan(self, plan):
        # Returns a list of idxs of success groups
        # plan: List[Dict[str: List[str]]] each object is {category_theme: [words]}

        def get_result(group_words):
            print(group_words)
            user_input = input("Was it failed, Y or N: ")
            return True if user_input == "Y" or user_input == "y" else False 
        
        successful_idxs = []
        for i in range(0, len(plan)):
            category, group_words = list(plan[i].items())[0]
            failed = get_result(group_words) #TODO: add multion integration
            if failed:
                break 
            
            successful_idxs.append(i)
        return successful_idxs
        


    def get_remaining_words(self, plan, success_group_idxs):
        solved_words = set()
        for idx in success_group_idxs:
            category, group = list(plan[idx].items())[0]
            solved_words.update(set(group))
        
        return list(set(self.remaining_words) - solved_words)


    def get_failed_group(self, plan, success_group_idxs):
        # Returns the failed {category: [group_words]} group 
        if len(success_group_idxs) == 0:
            failed_idx = 0
        else:
            failed_idx = max(success_group_idxs) + 1
            assert self.groups_correct < 4
        
        return plan[failed_idx]
    
    def update_state(self, plan, success_group_idxs):
        self.groups_correct += len(success_group_idxs)
        # check if game is over
        if self.groups_correct == 4: return  

        # update the remaining words and add failed group to planner memory
        remaining_words = self.get_remaining_words(plan, success_group_idxs)
        self.remaining_words = remaining_words
        self.planner.update_all_words(remaining_words)
        failed_group = self.get_failed_group(plan, success_group_idxs)
        self.planner.update_failed_group(failed_group)
        
        # increment mistakes
        self.num_mistakes += 1
    
    def main(self):
        while(self.groups_correct < 4 and self.num_mistakes < 4):
            generated_plan = self.planner.driver()
            success_group_idxs = self.execute_plan(generated_plan)
            self.update_state(generated_plan, success_group_idxs)
        
        if self.groups_correct == 4:
            print("Congratulations! You solved the puzzle.")
        else:
            print("Try again next time.")
        


    


if __name__ == "__main__":
    words = ["WAX", "MUMMY", "GIFT", "ANCHOR", "BURRITO", "PRESENT", "CLAY", "PAPYRUS", "SPRAIN", "FLAIR", "MODERATE", "TALENT", "INSTINCT", "PARCHMENT", "HOST", "FACULTY"]
    game_engine = Engine(words)
    pdb.set_trace()
    game_engine.main()