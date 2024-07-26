from model import Jury, Debate
import pdb 

def test_jury():
    plan = [{'WRITING MATERIALS': ['PAPYRUS', 'PARCHMENT', 'CLAY', 'WAX']}, {'PRESENT': ['GIFT', 'PRESENT', 'HOST', 'MODERATE']}, {'ABILITIES': ['FLAIR', 'TALENT', 'INSTINCT', 'FACULTY']}, {'BURRITO RELATED': ['MUMMY', 'BURRITO', 'SPRAIN', 'ANCHOR']}]
    jury = Jury()
    verdict = jury.group_judge(plan)

def test_debate():
    words = ["WAX", "MUMMY", "GIFT", "ANCHOR", "BURRITO", "PRESENT", "CLAY", "PAPYRUS", "SPRAIN", "FLAIR", "MODERATE", "TALENT", "INSTINCT", "PARCHMENT", "HOST", "FACULTY"]
    debater = Debate(words, num_rounds=2, num_agents=3)
    pdb.set_trace()
    agent_contexts = debater.driver()
if __name__ == "__main__":
    #test_jury()
    test_debate()