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
    recipeTypeQuery = "SELECT recipeTypeID, recipeTypeName FROM recipetype ORDER BY recipeTypeName;"
    recipeTypes = execute_query(db_connection, recipeTypeQuery).fetchall()
    cuisineTypeQuery = "SELECT cuisineTypeID, cuisineTypeName FROM cuisinetype ORDER BY cuisineTypeName;"
    cuisineTypes = execute_query(db_connection, cuisineTypeQuery).fetchall()
    avoidTypeQuery = "SELECT restrictionID, restrictionName FROM foodstoavoid ORDER BY restrictionName;"
    avoidTypes = execute_query(db_connection, avoidTypeQuery).fetchall()
    return [recipeTypes, cuisineTypes, avoidTypes]

# Check if a recipe already exists in the database
def does_recipe_exist(recipeURL) -> []:
    db_connection = connect_to_database()
    existQuery = "SELECT recipeID, isDeleted FROM recipes where url = '" + recipeURL + "';"
    result = execute_query(db_connection, existQuery).fetchone()
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
    print(recipeURL)
    updateQuery = "UPDATE recipes SET isDeleted = 0 WHERE url = '" + recipeURL + "';"
    execute_query(db_connection, updateQuery)
    return

# Add recipe restrictions
def add_recipe_restrictions(recipeURL, recipeRestrictions):
    db_connection = connect_to_database()
    if len(recipeRestrictions) > 0:
        getIdQuery = "SELECT recipeID FROM recipes WHERE url = '" + recipeURL + "';"
        recipeID = execute_query(db_connection, getIdQuery).fetchone()
        insertQuery = "INSERT INTO reciperestrictions (recipeID, restrictionID) values "
        for restriction in recipeRestrictions:
            print("recipeID = " + str(recipeID[0]) + ", restrictionID = " + str(restriction))
            insertQuery = insertQuery + "(" + str(recipeID[0]) + ", " + str(restriction) + "), "
        insertQuery = insertQuery[:-2]
        insertQuery += ";"
        print(insertQuery)
        execute_query(db_connection, insertQuery)
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
            print('Recipe undeleted.')
        else:
            # Recipe already exists and it's not deleted.
            print('Recipe already present.')
    else:
        # Recipe doesn't exist. Add it to the database.
        recipeName = request.form['recipeName']
        recipeType = request.form['type']
        cuisineType = request.form['cuisine']
        recipeRestrictions = request.form.getlist('avoid')
        print(request.form)
        print(recipeRestrictions)
        add_recipe(recipeName, recipeURL, recipeType, cuisineType)
        add_recipe_restrictions(recipeURL, recipeRestrictions)
    # flash("Recipe added successfully!")
    return redirect('/')