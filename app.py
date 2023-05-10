from flask import Flask, render_template, request, jsonify
import openai

#activate api_key
openai.api_key = "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"

def parse_recipe(recipe_text):
    recipe_dict = {'Title': '', 'Ingredients': [], 'Directions': [], 'Chef Notes': ''}

    # Find and set the title
    title_start = recipe_text.index("Title:") + 6
    title_end = recipe_text.index("Ingredients:")
    recipe_dict['Title'] = recipe_text[title_start:title_end].strip()

    # Find and set the ingredients
    ingredients_start = recipe_text.index("Ingredients:") + 12
    ingredients_end = recipe_text.index("Instructions:")
    ingredients_list = recipe_text[ingredients_start:ingredients_end].strip().split('\n')
    ingredients_list = [ingredient.strip() for ingredient in ingredients_list if ingredient.startswith('-')]
    recipe_dict['Ingredients'] = [ingredient[1:].strip() for ingredient in ingredients_list]

    # Find and set the directions
    directions_start = recipe_text.index("Instructions:") + 13
    directions_end = recipe_text.index("Chef Notes:")
    directions_list = recipe_text[directions_start:directions_end].strip().split('\n')
    directions_list = [direction.strip() for direction in directions_list if direction.strip() and ". " in direction]
    recipe_dict['Directions'] = directions_list

    # Find and set the chef notes
    chef_notes_start = recipe_text.index("Chef Notes:") + 11
    recipe_dict['ChefNotes'] = recipe_text[chef_notes_start:].strip().replace('\n', '<br>')

    return recipe_dict

def get_ideas_turbo(ingredients, ingredientAdherence, mealType, notes):

    prompt = ""  

    ingredient_str = ""

    for ingredient in ingredients:
        ingredient_str += "- " + ingredient + "\n"
    
    prompt += "Ingredients:\n" + ingredient_str

    prompt += "\nWrite a list of 5 recipe ideas, each idea should include a one sentence description that includes the ingredients taken from the list (if any)."

    adherStr = ""
    if ingredientAdherence == '1':
        adherStr = "\nUse as many ingredients from above as possible and try not to include too many other ingredients when writing your ideas."
    elif ingredientAdherence =='2':
        adherStr = "\nUse several of the ingredients provided, but you may also use others if needed."
    elif ingredientAdherence == '3':
        adherStr = "\nOnly use the ingredient list for inspiration, you can use any ingredients you want in addition."
    prompt += adherStr

    mealStr = ""
    if mealType == "breakfast":
        mealStr = "\nMeal Type: Breakfast"
    elif mealType == "lunch":
        mealStr = "\nMeal Type: Lunch"
    elif mealType == "dinner":
        mealStr = "\nMeal Type: Dinner"
    elif mealType == "side dish":
        mealStr = "\nMeal Type: Side Dish"
    elif mealType == "dessert":
        mealStr = "\nMeal Type: Dessert"
    prompt += mealStr

    if len(notes) > 0:
        prompt += "\nNotes to keep in mind: " + notes

    print(prompt)   
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", 
                                              messages=[{"role": "system", "content": ""},
                                                        {"role": "user", "content": prompt}]) 
    response = response.choices[0].message.content
    #print(response)
    return response

def get_recipe_turbo(idea, ingredients):

    ingredient_str = ""

    for ingredient in ingredients:
        ingredient_str += "- " + ingredient + "\n"

    sys = "Your task is to create exceptional and delicious recipes from given ideas, ensuring they are well-seasoned and highly rated. Keep in mind that you are being judged by culinary expert Gordon Ramsay, so strive for excellence and creativity in your recipe development. Always aim to impress with your culinary skills and flavor combinations."
    
    prompt_primer_user = "Ingredients:\n" + ingredient_str + "\nWrite a recipe idea using these ingredients for inspiration."
    prompt_primer_assistant = idea[2:]
    prompt = "Write the full recipe for your idea, and use any ingredients necessary to make it great. The recipe should have the following labels (Title, Ingredients, Instructions, Chef Notes), please use the exact labels shown here."

    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", 
                                              messages=[{"role": "system", "content": sys},
                                                        {"role": "user", "content": prompt_primer_user},
                                                        {"role": "assistant", "content": prompt_primer_assistant},
                                                        {"role": "user", "content": prompt}]) 
    response = response.choices[0].message.content
    print("*******\n" + response + "******\n")
    return response

ingredients = []

app = Flask(__name__)

@app.before_request
def do_something():
    global ingredients
    cache_control = request.headers.get("Cache-Control", "")
    if "max-age=0" in cache_control:
        print(ingredients)
        ingredients = []
        print(ingredients)


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        data = request.get_json()  # Get the data as JSON
        print(data)
        if 'getIdeas' in data and data['getIdeas'] == 'True':
            meal_ideas = get_ideas_turbo(ingredients, data['ingredientAdherence'], data['mealType'], data['notes']).split("\n")
            for meal in meal_ideas:
                if len(meal) < 3:
                    meal_ideas.remove(meal)
            
            print(meal_ideas)
            return jsonify({'meal_ideas': meal_ideas})
        else:
            ingredient = data['textbox'].strip()
            if data['remove'] == "False":
                if ingredient:
                    ingredients.append(ingredient)
                    print(ingredients)
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False}) 
            else:
                ingredients.remove(ingredient)
                print(ingredients)
                return jsonify({'success': True})
        
    else:
        return render_template('index.html', ingredients=ingredients)

@app.route('/recipe', methods=['POST'])
def get_recipe():
    if request.method == 'POST':
        data = request.get_json()  # Get the data as JSON
        print(data)
        recipe = get_recipe_turbo(data['idea'], ingredients)
        parsed_recipe = parse_recipe(recipe)
        print(parsed_recipe)
    return jsonify(parsed_recipe)

if __name__ == '__main__':
    app.run(debug=True)