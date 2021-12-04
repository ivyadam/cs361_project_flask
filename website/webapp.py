from flask import Flask, render_template, url_for, request, redirect, jsonify, flash
from db_connector.db_connector import connect_to_database, execute_query
from flask_restful import Resource, Api
from flask_cors import CORS
import json
import requests

# Create the web application
webapp = Flask(__name__)

# Get recipe details
def get_recipe_details(recipeURL):
    newUrl = recipeURL
    reqRecipeJSON = {'URL': newUrl}
    recipeData = requests.post('https://cs361recipescraper.herokuapp.com/scrape', json=reqRecipeJSON)
    parsedRecipe = json.loads(recipeData.text)
    return parsedRecipe

# Query the random recipe generator service
def query_random_service(arraySize):
    randomReqJSON = {"random_array": {"array_length": arraySize}}
    reqData = requests.post('https://cs360-random-recipe-generator.herokuapp.com/', json=randomReqJSON)
    parsedResponse = json.loads(reqData.text)
    returnIndex = parsedResponse['random_array']['return_index']
    return returnIndex

# Create types_list
def create_types_list(types):
    if len(types) > 0:
        typeQuery = "in ("
        for typeID in types:
            typeQuery = typeQuery + str(typeID) + ", "
        typeQuery = typeQuery[:-2]
        typeQuery += ") "
    else:
        typeQuery = ""
    return typeQuery

# Get array of recipes from the database
def get_recipe_array(recipeTypes, cuisineTypes, avoidTypes) -> []:
    db_connection = connect_to_database()
    recipeQuery = create_types_list(recipeTypes)
    if len(recipeQuery) > 0:
        recipeQuery = "recipeType " + recipeQuery
        addAnd = True
    cuisineQuery = create_types_list(cuisineTypes)
    if len(cuisineQuery) > 0:
        cuisineQuery = "cuisineType " + cuisineQuery
        if addAnd:
            cuisineQuery = " AND " + cuisineQuery
        addAnd = True
    avoidQuery = create_types_list(avoidTypes)
    if len(avoidQuery) > 0:
        avoidQuery = "recipeID NOT IN (SELECT recipeID FROM reciperestrictions WHERE restrictionID " + avoidQuery + ")"
        if addAnd:
            avoidQuery = " AND " + avoidQuery
    if(len(recipeQuery) > 0 or len(cuisineQuery) > 0 or len(avoidQuery) > 0):
        selectQuery = "SELECT url FROM recipes WHERE " + recipeQuery + cuisineQuery + avoidQuery + ";"
    else:
        selectQuery = "SELECT url FROM recipes;"
    recipeIdList = execute_query(db_connection, selectQuery).fetchall()
    return recipeIdList

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
            insertQuery = insertQuery + "(" + str(recipeID[0]) + ", " + str(restriction) + "), "
        insertQuery = insertQuery[:-2]
        insertQuery += ";"
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
    parsedRecipe = get_recipe_details(request.form['url'])
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
        add_recipe(recipeName, recipeURL, recipeType, cuisineType)
        add_recipe_restrictions(recipeURL, recipeRestrictions)
    return render_template('add_successful.html')

# Handler for settings
@webapp.route('/settings')
def settings():
    db_details = get_sidebar_recipe_details()
    recipeTypes = db_details[0]
    cuisineTypes = db_details[1]
    avoidTypes = db_details[2]        
    return render_template('settings.html', 
        recipeTypes = recipeTypes, 
        cuisineTypes = cuisineTypes, 
        avoidTypes = avoidTypes)

# Handler for adding recipe type
@webapp.route('/add_recipe_type', methods=['POST'])
def addRecipeType():
    db_connection = connect_to_database()
    insertQuery = "INSERT INTO recipetype (recipeTypeName) VALUES"
    insertQuery = insertQuery + "('" + str(request.form['recipeType']) + "');"
    execute_query(db_connection, insertQuery)
    return redirect('/settings')

# Handler for adding cuisine type
@webapp.route('/add_cuisine_type', methods=['POST'])
def addCuisineType():
    db_connection = connect_to_database()
    insertQuery = "INSERT INTO cuisinetype (cuisineTypeName) VALUES"
    insertQuery = insertQuery + "('" + str(request.form['cuisineType']) + "');"
    execute_query(db_connection, insertQuery)
    return redirect('/settings')

# Handler for adding restriction type
@webapp.route('/add_restriction_type', methods=['POST'])
def addRestrictionType():
    db_connection = connect_to_database()
    insertQuery = "INSERT INTO foodstoavoid (restrictionName) VALUES"
    insertQuery = insertQuery + "('" + str(request.form['restrictionType']) + "');"
    execute_query(db_connection, insertQuery)
    return redirect('/settings')

# Handler for deleting recipe type
@webapp.route('/delete_recipe_type', methods=['POST'])
def deleteRecipeType():
    db_connection = connect_to_database()
    updateQuery = "UPDATE recipes SET recipeType = NULL WHERE recipeType = " + str(request.form['recipeTypeID']) + ";"
    execute_query(db_connection, updateQuery)
    deleteQuery = "DELETE FROM recipetype WHERE recipeTypeID = " + str(request.form['recipeTypeID']) + ";"
    execute_query(db_connection, deleteQuery)
    return redirect('/settings')

# Handler for deleting cuisine type
@webapp.route('/delete_cuisine_type', methods=['POST'])
def deleteCuisineType():
    db_connection = connect_to_database()
    updateQuery = "UPDATE recipes SET cuisineType = NULL WHERE cuisineType = " + str(request.form['cuisineTypeID']) + ";"
    execute_query(db_connection, updateQuery)
    deleteQuery = "DELETE FROM cuisinetype WHERE cuisineTypeID = " + str(request.form['cuisineTypeID']) + ";"
    execute_query(db_connection, deleteQuery)
    return redirect('/settings')

# Handler for deleting restriction type
@webapp.route('/delete_restriction_type', methods=['POST'])
def deleteRestrictionType():
    db_connection = connect_to_database()
    deleteQuery = "DELETE FROM reciperestrictions WHERE restrictionID = " + str(request.form['restrictionID']) + ";"
    execute_query(db_connection, deleteQuery)
    deleteQuery = "DELETE FROM foodstoavoid WHERE restrictionID = " + str(request.form['restrictionID']) + ";"
    execute_query(db_connection, deleteQuery)
    return redirect('/settings')

# Handler for generating random recipe
@webapp.route('/generate_random', methods=['POST'])
def generateRandom():
    db_connection = connect_to_database()
    recipeTypes = request.form.getlist('recipeTypes')
    cuisineTypes = request.form.getlist('cuisineTypes')
    avoidTypes = request.form.getlist('avoidTypes')
    recipeList = get_recipe_array(recipeTypes, cuisineTypes, avoidTypes)
    recipeIndex = query_random_service(len(recipeList))
    outputRecipe = recipeList[recipeIndex][0]
    parsedRecipe = get_recipe_details(outputRecipe)
    db_details = get_sidebar_recipe_details()
    recipeTypes = db_details[0]
    cuisineTypes = db_details[1]
    avoidTypes = db_details[2]  
    return render_template('view_recipe.html', 
        imageURL = parsedRecipe['recipe']['image_url'],
        name = parsedRecipe['recipe']['name'],
        ingredients = parsedRecipe['recipe']['recipeIngredients'],
        instructions = parsedRecipe['recipe']['recipeInstructions'],
        recipeURL = parsedRecipe['recipe']['recipe_url'],
        recipeTypes = recipeTypes, 
        cuisineTypes = cuisineTypes, 
        avoidTypes = avoidTypes
    )

# Handler for marking a recipe as deleted
@webapp.route('/delete_recipe', methods=['POST'])
def deleteRecipe():
    db_connection = connect_to_database()
    deleteQuery = "UPDATE recipes SET isDeleted = 1 WHERE url = '" + request.form['url'] + "';"
    execute_query(db_connection, deleteQuery)
    print("Recipe deleted.")
    return render_template('delete_successful.html')