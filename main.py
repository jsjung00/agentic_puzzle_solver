from openai import OpenAI
from dotenv import load_dotenv
import json 
import pdb 
from model import Replanner, Orchestrator, Debate, Verifier, Ranker

'''
'''
load_dotenv()

class Engine:
    def __init__(self, all_words: list[str]):
        self.groups_correct = 0
        self.num_mistakes = 0
        self.remaining_words = all_words
        self.failed_groups = []
    
    def update_remaining_words(self, success_group: list[str]):
        new_remaining_words = [word for word in self.remaining_words if word not in success_group]
        self.remaining_words = new_remaining_words

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
            # generate the list of groups to try 
            orchestrator = Orchestrator(self.remaining_words, self.groups_correct, self.failed_groups)

            groups_solved, failed_group = orchestrator.run_round()
            if failed_group:
                self.failed_groups.append(failed_group)

            # update available words
            for group in groups_solved:
                self.update_remaining_words(group)

            self.groups_correct += len(groups_solved)

            if self.groups_correct < 4:
                self.num_mistakes += 1

        if self.groups_correct == 4:
            print("Congratulations! You solved the puzzle.")
        else:
            print("Try again next time.")
        


    


if __name__ == "__main__":
    words = ["WAX", "MUMMY", "GIFT", "ANCHOR", "BURRITO", "PRESENT", "CLAY", "PAPYRUS", "SPRAIN", "FLAIR", "MODERATE", "TALENT", "INSTINCT", "PARCHMENT", "HOST", "FACULTY"]
    game_engine = Engine(words)
    game_engine.main()