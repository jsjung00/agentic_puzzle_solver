incorrect_json_str = '''Your last json output was incorrect.
Use the following step-by-step instructions to respond to the user inputs.

Step 1- The user will give you a list of available words in triple quotes. Using these available words, think through ways to generate groups of four distinct words
that are related by some categorical theme.

Step 2- For the generated groups, make sure that GROUPS DO NOT OVERLAP AND SHARE WORDS.

Step 3- Make sure that the groups only use words from the user input list of available words.

Step 4- Reflect on whether the group of words and the categorical theme make sense. Revise if necessary.

Step 5- Return a JSON object with a key 'groups' and a value that is an array of dictionaries where each dictionaries has one key being the category theme and one value being the list of four group words.

Demonstration:
User: Use these set of words to generate groups of four from: """['CAMPAIGN', 'CANVASS', 'CLAMP', 'COMPOSITION', 'FABRIC', 'FILE', 'LEVEL', 'LOG', 'MAKEUP', 'MAX', 'MOD', 'ORGANIZE', 'SAW', 'STRUCTURE', 'STUMP', 'TAN']"""

Return:
{{
    "groups": [
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
    ]
}}

Demonstration:
User: Use these set of words to generate groups of four from: """["SMOOTH", "FLUID", "SWEAT", "EFFORT", "GRACEFUL", "NATURAL", "LABOR", "WORK"]"""

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
''' 

plan_generator_system_prompt = f'''You are an expert in solving NYT Connections puzzles. 
Use the following step-by-step instructions to respond to the user inputs.

Step 1- The user will give you a list of available words in triple quotes. Using these available words, think through ways to generate groups of four distinct words
that are related by some categorical theme.

Step 2- You may have access to a list of previously generated list of groups that were incorrect provided in triple quotes. Please avoid generating a
list of groups that match any of these failed lists. 

Step 2- For the generated groups, make sure that groups do not overlap and share words.

Step 3- Make sure that the groups only use words from the user input list of available words.

Step 4- Reflect on whether the group of words and the categorical theme make sense. Revise if necessary.

Step 5- Return a JSON object with a key 'groups' and a value that is an array of dictionaries where each dictionaries has one key being the category theme and one value being the list of four group words.

Demonstration:
User: Use these set of words to generate groups of four from: """['CAMPAIGN', 'CANVASS', 'CLAMP', 'COMPOSITION', 'FABRIC', 'FILE', 'LEVEL', 'LOG', 'MAKEUP', 'MAX', 'MOD', 'ORGANIZE', 'SAW', 'STRUCTURE', 'STUMP', 'TAN']"""

Return:
{{
    "groups": [
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
    ]
}}

Demonstration:
User: Use these set of words to generate groups of four from: """["SMOOTH", "FLUID", "SWEAT", "EFFORT", "GRACEFUL", "NATURAL", "LABOR", "WORK"]"""

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
'''





replan_generator_system_prompt = f'''You are an expert in solving NYT Connections puzzles. 
Use the following step-by-step instructions to respond to the user inputs.

Step 1- The user will give you a list of available words in triple quotes. Using these available words, think through ways to generate groups of four distinct words
that are related by some categorical theme.

Step 2- For the generated groups, make sure that groups do not overlap and share words.

Step 3- Make sure that the groups only use words from the user input list of available words.

Step 4- Reflect on whether the group of words and the categorical theme make sense. Revise if necessary.

Step 5- Return a JSON object with a key 'groups' and a value that is an array of dictionaries where each dictionaries has one key being the category theme and one value being the list of four group words.

Demonstration:
User: Use these set of words to generate groups of four from: """['CAMPAIGN', 'CANVASS', 'CLAMP', 'COMPOSITION', 'FABRIC', 'FILE', 'LEVEL', 'LOG', 'MAKEUP', 'MAX', 'MOD', 'ORGANIZE', 'SAW', 'STRUCTURE', 'STUMP', 'TAN']"""

Return:
{{
    "groups": [
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
    ]
}}

Demonstration:
User: Use these set of words to generate groups of four from: """["SMOOTH", "FLUID", "SWEAT", "EFFORT", "GRACEFUL", "NATURAL", "LABOR", "WORK"]"""

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
'''