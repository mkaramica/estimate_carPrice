from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import time

#db_stored_name = "vin100k"
db_stored_name = "vinaudit_database"


def timer_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        print(f"Execution time: {(end_time - start_time):6f} sec.")
        return result
    return wrapper

def connect_to_database():
    vinaudit_db = mysql.connector.connect(
        host="localhost",
        user="mk",
        password="admin"
    )
    return vinaudit_db


def estimate_price(target_mileage, price_list,mileage_list):
    target_mileage = int(target_mileage)
    mean_mileage = sum(mileage_list) / len(mileage_list)
    mean_price = sum(price_list) / len(price_list)
    
    # Calculate the numerator and denominator of the slope equation
    numerator = sum([(mileage - mean_mileage) * (price - mean_price) for mileage, price in zip(mileage_list, price_list)])
    denominator = sum([(mileage - mean_mileage) ** 2 for mileage in mileage_list])
    
    slope = numerator / denominator
    y_intercept = mean_price - slope * mean_mileage
    
    estimated_price = slope * target_mileage + y_intercept
    estimated_price = round(estimated_price/100) * 100
    
    return estimated_price

@timer_decorator
def find_similarCases(db, db_stored_name, target_case):
    requested_makeModel = target_case['makeModel']
    requested_year = target_case['year']
    requested_make = target_case['make']
    requested_model = target_case['model']
    requested_mileage = target_case['mileage']
    
    mycursor = db.cursor()
    mycursor.execute(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_stored_name}'")
    dbExists = mycursor.fetchone()
    
    if not dbExists:
        print(f"Warning! Data base '{db_stored_name}' does not exist!")
        print("*"*80)
        return None
    
    mycursor.execute(f"USE {db_stored_name}")
    
    
    if requested_makeModel:
        sql_makeModel = f"CONCAT(make, ' ', model) = '{requested_makeModel}' " 
    else:
        sql_makeModel = f"make = '{requested_make}' AND model = '{requested_model}' "
        
    
    
    if requested_mileage:
        sql_command = f"SELECT year, make, model, price, mileage, city, state, ABS(mileage - {requested_mileage}) as diff_mileage FROM cars "
        sql_command += f"WHERE price IS NOT NULL AND "
        sql_command += f"mileage IS NOT NULL AND "
        sql_command += f"year = {requested_year} AND "
        sql_command += sql_makeModel
        sql_command += "ORDER BY diff_mileage LIMIT 100"
    else:
        sql_command = f"SELECT AVG(price) AS price_avg FROM cars "
        sql_command += f"WHERE price IS NOT NULL AND "
        sql_command += f"year = {requested_year} AND "
        sql_command += sql_makeModel
        
        mycursor.execute(sql_command)
        records = mycursor.fetchall()
        print(records)
        if len(records) == 0 or records[0][0] == None:
            record_dicts = None
            estimated_price = None
            return record_dicts, estimated_price
        
        estimated_price = round(int(records[0][0])/100) * 100
        #---------------------------------------------------
        sql_command = f"SELECT year, make, model, price, mileage, city, state, ABS(price - {estimated_price}) as diff_price FROM cars "
        sql_command += f"WHERE price IS NOT NULL AND "
        sql_command += f"year = {requested_year} AND "
        sql_command += sql_makeModel
        sql_command += "ORDER BY diff_price LIMIT 100"

    
    
    mycursor.execute(sql_command)
    records = mycursor.fetchall()
    
    if len(records) == 0:
        record_dicts = None
        estimated_price = None
        return record_dicts, estimated_price
        
     
    record_dicts = [
    {
      'year':  record[0],
      'make': record[1],
      'model': record[2],
      'price':  record[3],
      'mileage':  record[4],
      'city':  record[5],
      'state':  record[6]
    } 
    for record in records] 
    
    target_case['make'] = target_case['make'] or record_dicts[0]['make']
    target_case['model'] = target_case['model'] or record_dicts[0]['model']
    
    
    if requested_mileage:
        price_list = [int(record[3]) for record in records]
        mileage_list = [int(record[4]) for record in records]
        
        estimated_price = estimate_price(requested_mileage, price_list,mileage_list)   
        estimated_price = round(estimated_price / 100) * 100


    return record_dicts, estimated_price
    


app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    requested_yearMakeModel = request.args.get('year_make_model')
    requested_year = request.args.get('year')
    requested_make = request.args.get('make')
    requested_model = request.args.get('model')
    requested_mileage = request.args.get('mileage')
    
    if not ( requested_yearMakeModel or
    (requested_year and requested_make and requested_model)):
        message = "Please enter the required items!"
        return render_template('index.html', message = message)
        
    
    requested_makeModel = ''
    
    if requested_yearMakeModel:
        splitInput = requested_yearMakeModel.split(" ")
        if (len(splitInput) < 3) or (not splitInput[0].isnumeric()):
            message = "Wrong input!"
            return render_template('index.html', message = message)
        
        requested_year = splitInput[0]
        requested_makeModel = " ".join(splitInput[1:])
        

    target_case = {
        'makeModel': requested_makeModel,
        'year': requested_year,
        'make': requested_make,
        'model': requested_model,
        'mileage': requested_mileage
    }
    
    
    with connect_to_database() as vinaudit_db:
        record_dicts, estimated_price = find_similarCases(vinaudit_db, db_stored_name, target_case)
        
    
    if not (record_dicts and estimated_price):
        message = "No record found!"
        return render_template('index.html', message = message)
    
    return render_template('results.html', 
                           target_case = target_case,
                           estimated_price = estimated_price,
                           record_dicts = record_dicts)
        

if __name__ == '__main__':
    app.run(debug=True)
