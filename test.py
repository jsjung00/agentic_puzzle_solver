from model import Jury
import pdb 

def test_jury():
    plan = [{'WRITING MATERIALS': ['PAPYRUS', 'PARCHMENT', 'CLAY', 'WAX']}, {'PRESENT': ['GIFT', 'PRESENT', 'HOST', 'MODERATE']}, {'ABILITIES': ['FLAIR', 'TALENT', 'INSTINCT', 'FACULTY']}, {'BURRITO RELATED': ['MUMMY', 'BURRITO', 'SPRAIN', 'ANCHOR']}]
    jury = Jury()
    verdict = jury.group_judge(plan)

if __name__ == "__main__":
    test_jury()