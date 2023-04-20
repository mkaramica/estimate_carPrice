# Author: Mahdi Karami; email: mahdi.karami.ca@gmail.com

from flask import Flask, render_template, request
import mysql.connector
from dotenv import load_dotenv
import time
import os


app = Flask(__name__)

def timer_decorator(func):
    """
    Returns the execution time for any arbitrary function.
    This decorator returns the execution time for any given function .
    This is especially useful to compare the performance of column indexing when executing queries on the large databases.
    """
    
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        print("*"*30)
        print(f"Execution time: {(end_time - start_time):6f} sec.")
        print("*"*30)
        return result
    return wrapper


class PriceEstimation:
    """
    Estimates the price of a used car based on its features.
    This class provides required funciton(s) for estimating the price of a given car.
    Different methods, including linear regression and machine learning approaches can be placed here.
    It is recommended to decorate the funcitons with @staticmethod decorator to make it easy to use them.
    """
    
    @staticmethod
    def linearReg(target_mileage, price_list,mileage_list):
        """
        Estimates price by utilizing 1-D linear regression approach.
        """
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


class DatabaseController:
    """
    Handles everything about the database.
    All database operations are carried out by this class;
    Including authentication, connection, disconnection, and query execution.
    """
    def __init__(
        self, 
        db_name=None, 
        host=None, 
        user=None, 
        password=None
    ):
    
        """
        Authentication setup for the databse.
        The information are stored in a .env file and retrieved as environmental variables.
        """
        
        load_dotenv()
        
        self.db_name = db_name or os.getenv('DB_NAME')
        self.db_host = host or os.getenv('DB_HOST')
        self.db_user = user or os.getenv('DB_USER')
        self.db_password = password or os.getenv('DB_PASSWORD')
        self.connection = None


    def connect(self):
        self.connection = mysql.connector.connect(
            host=self.db_host,
            user=self.db_user,
            password=self.db_password,
            database=self.db_name
        )
        
       
    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    @timer_decorator
    def execute_query(self, target_case):
        """
        Perform query excecution to find similar cars and the corresponding estimated price.
        """
        cursor = self.connection.cursor()
       
        if target_case["makeModel"]:
            sql_makeModel = "CONCAT(make, ' ', model) = %(makeModel)s " 
        else:
            sql_makeModel = "make = %(make)s AND model= %(model)s "
       
       
        if target_case["mileage"]:
            sql_query = "SELECT year, make, model, price, mileage, city, state, \
                ABS(mileage - %(mileage)s) as diff_mileage FROM cars \
                WHERE price IS NOT NULL AND mileage IS NOT NULL AND \
                year= %(year)s AND "  + sql_makeModel +  "ORDER BY diff_mileage LIMIT %(max_records)s"
        else:
            sql_query = "SELECT AVG(price) FROM cars WHERE price IS NOT NULL AND \
                year= %(year)s AND " + sql_makeModel

            cursor.execute(sql_query, target_case)
            query_result = cursor.fetchall()
            
            if query_result[0][0] == None:
                cursor.close()
                return {'estimated_price': None, 'searched_cars': None}
            
            estimated_price = round(int(query_result[0][0])/100) * 100
            
            sql_query = f"SELECT year, make, model, price, mileage, city, state, \
                ABS(price - '{estimated_price}') as diff_price FROM cars WHERE price IS NOT NULL AND \
                year= %(year)s AND "  + sql_makeModel +  "ORDER BY diff_price LIMIT %(max_records)s" 
            
            

        cursor.execute(sql_query, target_case)
        query_result = cursor.fetchall()
        cursor.close()
        
        if query_result[0][0] == None:
                return {'estimated_price': None, 'searched_cars': None}
                
        
        searched_cars = [
        {
          'year':  record[0],
          'make': record[1],
          'model': record[2],
          'price':  record[3],
          'mileage':  record[4],
          'city':  record[5],
          'state':  record[6]
        } 
        for record in query_result] 
        
        
        if target_case['mileage']:
            price_list = [int(record[3]) for record in query_result]
            mileage_list = [int(record[4]) for record in query_result]
            
            estimated_price = PriceEstimation.linearReg(target_case['mileage'], price_list,mileage_list)   
            estimated_price = round(estimated_price / 100) * 100
            
            
        return {'estimated_price': estimated_price, 'searched_cars': searched_cars}
        

    def __enter__(self):
        """
        This dunder help open the class by 'with' statement.
        """
        self.connect()
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        This dunder help open the class by 'with' statement.
        """
        self.disconnect()


class WebApp:
    """
    Controls workflow of the web application.
    """
    def __init__(
        self, 
        db_name=None, 
        host=None, 
        user=None, 
        password=None
    ):
    
        """
        Database initialization
        """
        self.db_controller = DatabaseController(
            db_name=db_name,
            host=host,
            user=user,
            password=password
        )
        
    
    def validate_request(self, requestArgs):
        """
        Validates the http request received by the class.
        It then builds self.target_case and self.warning_message accordingly.
        """
        requested_yearMakeModel = requestArgs.get('year_make_model')
        requested_year = requestArgs.get('year')
        requested_make = requestArgs.get('make')
        requested_model = requestArgs.get('model')
        requested_mileage = requestArgs.get('mileage')
        
        if not ( requested_yearMakeModel or
        (requested_year and requested_make and requested_model)):
            self.target_case = None
            self.warning_message = "Please enter the required items!"
            return

            
        requested_makeModel = ''
        
        if requested_yearMakeModel:
            splitInput = requested_yearMakeModel.split(" ")
            if (len(splitInput) < 3) or (not splitInput[0].isnumeric()):
                self.target_case = None 
                self.warning_message = "Wrong input!"
                return
            
            requested_year = splitInput[0]
            requested_makeModel = " ".join(splitInput[1:])
            

        self.target_case = {
            'makeModel': requested_makeModel,
            'year': requested_year,
            'make': requested_make,
            'model': requested_model,
            'mileage': requested_mileage,
            'max_records': 
                int(requestArgs.get('max_records')) \
                if ( 
                    requestArgs.get('max_records') and
                    requestArgs.get('max_records').isnumeric()
                )
                else 100
        }
            
        self.warning_message = "All good!"
        return
        
          
    
    def perform_query(self):
        """
        Transfers the required query to the database, and gets the results.
        """
        with self.db_controller as db:
            query_results = db.execute_query(self.target_case)
            
        
        if query_results['estimated_price'] and \
           query_results['searched_cars']:
                   
            self.estimated_price =  query_results['estimated_price']
            self.searched_cars = query_results['searched_cars']
            
            if self.target_case['makeModel']:
                self.target_case['make'] = self.searched_cars[0]['make']
                self.target_case['model'] = self.searched_cars[0]['model']
            
            return 


        self.estimated_price = None
        self.searched_cars = None
        self.warning_message = "No record found!"
        return
        
    
    
    def run(self):
        app.run(debug=False)
        

web_app = WebApp()

@app.route('/', methods=['GET'])
def index():
    """
    Receives the http request and renders an appropriate html content accordingly.
    """
    web_app.validate_request(request.args)
    
    if web_app.target_case:
        web_app.perform_query()
        if web_app.estimated_price and\
            web_app.searched_cars:
            
            return render_template(
                'results.html', 
                target_case = web_app.target_case,
                estimated_price = web_app.estimated_price,
                record_dicts = web_app.searched_cars
                )

    return render_template(
        'index.html', 
        message = web_app.warning_message
    )


if __name__ == '__main__':
    web_app.run()
