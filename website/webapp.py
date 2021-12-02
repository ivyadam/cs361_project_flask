from flask import Flask, render_template, url_for, request, redirect, jsonify, flash
from db_connector.db_connector import connect_to_database, execute_query
from flask_restful import Resource, Api
from flask_cors import CORS
import json
import requests

# Create the web application
webapp = Flask(__name__)

# Capture information for the sidebar
def get_sidebar_recipe_details() -> []:
    db_connection = connect_to_database()
    recipeTypeQuery = "SELECT recipeTypeID, recipeTypeName FROM recipetype;"
    recipeTypes = execute_query(db_connection, recipeTypeQuery).fetchall()
    cuisineTypeQuery = "SELECT cuisineTypeID, cuisineTypeName FROM cuisinetype;"
    cuisineTypes = execute_query(db_connection, cuisineTypeQuery).fetchall()
    avoidTypeQuery = "SELECT restrictionID, restrictionName FROM foodstoavoid;"
    avoidTypes = execute_query(db_connection, avoidTypeQuery).fetchall()
    return [recipeTypes, cuisineTypes, avoidTypes]

# Check if a recipe already exists in the database
def does_recipe_exist(recipeURL) -> []:
    db_connection = connect_to_database()
    existQuery = "SELECT recipeID, isDeleted FROM recipes where url = '%s';"
    data = (recipeURL)
    result = execute_query(db_connection, existQuery, data).fetchone()
    if result == None:
        recipeFound = False
        isDeleted = False
    else:
        recipeFound = True
        if result[1] == 0:
            isDeleted = False
        else:
            isDeleted = True
    return [recipeFound, isDeleted]

# Add a recipe to the database
def add_recipe(recipeName, recipeURL, recipeType, cuisineType):
    db_connection = connect_to_database()
    insertQuery = "INSERT INTO recipes "
    insertQuery += "(recipeName, url, isDeleted, recipeType, cuisineType) VALUES "
    insertQuery += "(%s,%s,0,%s,%s);"
    data = (recipeName, recipeURL, recipeType, cuisineType)
    execute_query(db_connection, insertQuery, data)
    return

# Undelete a recipe
def undelete_recipe(recipeURL):
    db_connection = connect_to_database()
    updateQuery = "UPDATE recipes SET isDeleted = 0 WHERE url = %s;"
    data = (recipeURL)
    execute_query(db_connection, updateQuery, data)
    return

# Handler for homepage
@webapp.route('/')
def index():
        db_details = get_sidebar_recipe_details()
        recipeTypes = db_details[0]
        cuisineTypes = db_details[1]
        avoidTypes = db_details[2]        
        return render_template('home.html', recipeTypes = recipeTypes, cuisineTypes = cuisineTypes, avoidTypes = avoidTypes)

# Handler to retrieve recipe
@webapp.route('/get_recipe', methods=['POST'])
def getRecipe():
    newUrl = request.form['url']
    reqRecipeJSON = {'URL': newUrl}
    recipeData = requests.post('https://cs361recipescraper.herokuapp.com/scrape', json=reqRecipeJSON)
    parsedRecipe = json.loads(recipeData.text)
    db_details = get_sidebar_recipe_details()
    recipeTypes = db_details[0]
    cuisineTypes = db_details[1]
    avoidTypes = db_details[2]   
    return render_template('import_recipe.html', 
        imageURL = parsedRecipe['recipe']['image_url'],
        name = parsedRecipe['recipe']['name'],
        ingredients = parsedRecipe['recipe']['recipeIngredients'],
        instructions = parsedRecipe['recipe']['recipeInstructions'],
        recipeURL = parsedRecipe['recipe']['recipe_url'],
        recipeTypes = recipeTypes, 
        cuisineTypes = cuisineTypes, 
        avoidTypes = avoidTypes
    )

# Handler to add a recipe
@webapp.route('/add_recipe', methods=['POST'])
def addRecipe():
    recipeURL = request.form['recipeURL']
    existing = does_recipe_exist(recipeURL)
    if existing[0]:
        # Recipe already exists in the database. 
        if existing[1]:
            # If it's been deleted, reactivate it.
            undelete_recipe(recipeURL)
        else:
            # Recipe already exists and it's not deleted.
            print('Recipe already present.')
    else:
        # Recipe doesn't exist. Add it to the database.
        recipeName = request.form['recipeName']
        recipeType = request.form['type']
        cuisineType = request.form['cuisine']
        add_recipe(recipeName, recipeURL, recipeType, cuisineType)
    flash("Recipe added successfully!")
    return redirect('/')

# @webapp.route('/home')
# def home():
#     db_connection = connect_to_database()
#     query = "DROP TABLE IF EXISTS diagnostic;"
#     execute_query(db_connection, query)
#     query = "CREATE TABLE diagnostic(id INT PRIMARY KEY, text VARCHAR(255) NOT NULL);"
#     execute_query(db_connection, query)
#     query = "INSERT INTO diagnostic (text) VALUES ('MySQL is working');"
#     execute_query(db_connection, query)
#     query = "SELECT * from diagnostic;"
#     result = execute_query(db_connection, query)
#     for r in result:
#         print(f"{r[0]}, {r[1]}")
#     return render_template('home.html', result = result)

# @webapp.route('/db_test')
# def test_database_connection():
#     print("Executing a sample query on the database using the credentials from db_credentials.py")
#     db_connection = connect_to_database()
#     query = "SELECT * from bsg_people;"
#     result = execute_query(db_connection, query)
#     return render_template('db_test.html', rows=result)

# #display update form and process any updates, using the same function
# @webapp.route('/update_people/<int:id>', methods=['POST','GET'])
# def update_people(id):
#     print('In the function')
#     db_connection = connect_to_database()
#     #display existing data
#     if request.method == 'GET':
#         print('The GET request')
#         people_query = 'SELECT character_id, fname, lname, homeworld, age from bsg_people WHERE character_id = %s'  % (id)
#         people_result = execute_query(db_connection, people_query).fetchone()

#         if people_result == None:
#             return "No such person found!"

#         planets_query = 'SELECT planet_id, name from bsg_planets'
#         planets_results = execute_query(db_connection, planets_query).fetchall()

#         print('Returning')
#         return render_template('people_update.html', planets = planets_results, person = people_result)
#     elif request.method == 'POST':
#         print('The POST request')
#         character_id = request.form['character_id']
#         fname = request.form['fname']
#         lname = request.form['lname']
#         age = request.form['age']
#         homeworld = request.form['homeworld']

#         query = "UPDATE bsg_people SET fname = %s, lname = %s, age = %s, homeworld = %s WHERE character_id = %s"
#         data = (fname, lname, age, homeworld, character_id)
#         result = execute_query(db_connection, query, data)
#         print(str(result.rowcount) + " row(s) updated")

#         return redirect('/browse_bsg_people')

# @webapp.route('/delete_people/<int:id>')
# def delete_people(id):
#     '''deletes a person with the given id'''
#     db_connection = connect_to_database()
#     query = "DELETE FROM bsg_people WHERE character_id = %s"
#     data = (id,)

#     result = execute_query(db_connection, query, data)
#     return (str(result.rowcount) + "row deleted")
