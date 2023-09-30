from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user

import openai
import json

### Look into making the prompts + outputs higher quality + shorter at the same time
### 250 tokens for ideas
### 450 tokens for recipes
### fix delete button so that it removes the recipes from the user's db
### check for any old code regarding add/remove ingredients, there might be some left over in index.html

#activate api_key
openai.api_key = ""

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

    print("System: ", sys)
    print("User: ", prompt_primer_user)
    print("Assistant: ", prompt_primer_assistant)
    print("User: ", prompt)

    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", 
                                              messages=[{"role": "system", "content": sys},
                                                        {"role": "user", "content": prompt_primer_user},
                                                        {"role": "assistant", "content": prompt_primer_assistant},
                                                        {"role": "user", "content": prompt}]) 
    response = response.choices[0].message.content
    print("*******\n" + response + "******\n")
    return response

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session security

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)


# User model
class User(UserMixin, db.Model):
    id = db.Column(db.String(50), primary_key=True)
    password_hash = db.Column(db.String(128))
    recipes = db.Column(db.Text)

    def __init__(self, id, password):
        self.id = id
        self.password_hash = generate_password_hash(password)
        self.recipes = '[]'

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_recipes(self):
        return eval(self.recipes)

    def add_recipe(self, title, ingredients, directions, chef_notes):
        
        recipe = {
            'title': title,
            'ingredients': ingredients,
            'directions': directions,
            'chef_notes': chef_notes
        }
        recipes = self.get_recipes()
        recipes.append(recipe)
        self.recipes = str(recipes)

        print("Recipe*********\n\n", self.recipes, "\n\nRecipe*********")

    def clear_recipes(self):
        self.recipes = '[]'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user = User.query.get(current_user.id)
    recipes = user.get_recipes()

    if request.method == 'POST':
        data = request.get_json()  # Get the data as JSON
        print(data)
        if 'getIdeas' in data and data['getIdeas'] == 'True':
            ingredients = data['ingredients']  # Retrieve the ingredients from the JSON data
            meal_ideas = get_ideas_turbo(ingredients, data['ingredientAdherence'], data['mealType'], data['notes']).split("\n")
            meal_ideas = [meal for meal in meal_ideas if len(meal) >= 3]
            print(meal_ideas)
            return jsonify({'meal_ideas': meal_ideas})

    return render_template('index.html', recipes=recipes)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.get(username)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.get(username):
            return render_template('register.html', error='Username already exists')
        user = User(username, password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/add_recipe', methods=['POST'])
@login_required
def add_recipe():
    recipe_data = request.get_json()  # Get the recipe data from the request's JSON payload

    # Extract the recipe details from the recipe data
    title = recipe_data.get('title')
    ingredients = recipe_data.get('ingredients')
    directions = recipe_data.get('directions')
    chef_notes = recipe_data.get('chefNotes')

    user = User.query.get(current_user.id)
    user.add_recipe(title, ingredients, directions, chef_notes)
    db.session.commit()
    return jsonify({'message': 'Recipe added successfully'})  # Respond with a success message

@app.route('/recipe', methods=['POST'])
@login_required
def get_recipe():
    if request.method == 'POST':
        data = request.get_json()  # Get the data as JSON
        print(data)
        recipe = get_recipe_turbo(data['idea'], data['ingredients'])
        parsed_recipe = parse_recipe(recipe)
        print(parsed_recipe)
    return jsonify(parsed_recipe)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

@app.route('/delete_recipe/<int:recipe_id>', methods=['DELETE'])
@login_required
def delete_recipe(recipe_id):
    user = User.query.get(current_user.id)
    recipes = user.get_recipes()

    print("running")

    # Find the recipe with the given recipe_id
    recipe_index = recipe_id - 1  # Adjust index since recipe_id starts from 1
    if 0 <= recipe_index < len(recipes):
        del recipes[recipe_index]  # Delete the recipe from the list
        user.recipes = json.dumps(recipes)  # Update the user's recipes

        db.session.commit()
        return jsonify({'message': 'Recipe deleted successfully'}), 200  # Respond with a success message
    else:
        return jsonify({'error': 'Recipe not found'}), 404  # Respond with an error if recipe not found

