import mysql.connector



def connect_to_database():
    vinaudit_db = mysql.connector.connect(
        host="localhost",
        user="mk",
        password="admin"
    )
    return vinaudit_db
    

def create_database(db, db_stored_name):
    mycursor = db.cursor()
    mycursor.execute(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_stored_name}'")
    dbExists = mycursor.fetchone()
    
    if dbExists:
        print(f"Warning! Data base '{db_stored_name}' exists! Database creation neglected!")
        print("*"*80)
        return 0
    
    mycursor.execute(f"CREATE DATABASE {db_stored_name}")
    mycursor.execute(f"USE {db_stored_name}")
    
    sql_command = "CREATE TABLE cars ("
    sql_command += "vin VARCHAR(30) PRIMARY KEY, "
    sql_command += "year INT NULL, "
    sql_command += "make VARCHAR(200) NULL, "
    sql_command += "model VARCHAR(200) NULL, "
    sql_command += "trim VARCHAR(200) NULL, "
    sql_command += "price INT NULL, "
    sql_command += "mileage INT NULL, "
    sql_command += "city VARCHAR(200) NULL, "
    sql_command += "state VARCHAR(20) NULL ) "
    
    mycursor.execute(sql_command)
    
    print(f"Database '{db_stored_name}' created successfully!")
    print("*"*80)
    return 0
    

def insertData_into_database(db, db_stored_name, carData_dict, 
                   record_range = {"from":1, "to":0}):
    
    if (record_range["to"] == 0 or record_range["to"] > len(carData_dict["vins"])):
        record_range["to"]=len(carData_dict["vins"])
        
    mycursor = db.cursor()
    mycursor.execute(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db_stored_name}'")
    dbExists = mycursor.fetchone()
    
    if not dbExists:
        print(f"Warning! Data base '{db_stored_name}' does not exists! Data insertion neglected!")
        print("*"*80)
        return 0
        
    
    indx_start = record_range["from"]-1
    index_end = record_range["to"]
    
    vins = carData_dict["vins"][indx_start:index_end]
    years= carData_dict["years"][indx_start:index_end]
    makes = carData_dict["makes"][indx_start:index_end]
    models = carData_dict["models"][indx_start:index_end]
    trims = carData_dict["trims"][indx_start:index_end]
    prices = carData_dict["prices"][indx_start:index_end]
    mileages = carData_dict["mileages"][indx_start:index_end]
    cities = carData_dict["cities"][indx_start:index_end]
    states = carData_dict["states"][indx_start:index_end]
    
    rows = zip(vins, years, makes, models, trims, prices, mileages, cities, states)
    
    sql = "INSERT IGNORE INTO cars (vin, year, make, model, trim, price, mileage, city, state) "
    sql += "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    
    mycursor.execute(f"USE {db_stored_name}")
    mycursor.executemany(sql, [
    (vin, year, make, model, trim, price, mileage, city, state)
    for vin, year, make, model, trim, price, mileage, city, state 
    in rows])


    db.commit()
    print(f"{len(vins)} records (from row #{indx_start+1} to #{index_end}) inserted into '{db_stored_name}' database successfully!")
    print("-"*80)
    return 0

  
def readInfo_fromFile(fileName, nRowsMax = 1e8):
    
    vins = []
    years = []
    makes= []
    models = []
    trims = []
    prices = []
    mileages = []
    cities = []
    states = []
    
    
    with open(fileName, 'r', encoding='utf-8') as fFile:
        # Read the file line by line
        nline=0
        for line in fFile:
            if (nline==0):
                column_names=line.split("|")
            else: 
                cells = line.split("|")
                
                vins.append(cells[0]) 
                years.append(cells[1]) 
                makes.append(cells[2]) 
                models.append(cells[3]) 
                trims.append(cells[4]) 
                prices.append(cells[10]) 
                mileages.append(cells[11]) 
                cities.append(cells[7]) 
                states.append(cells[8]) 
                                
            if nline == nRowsMax:
                break
            
            nline +=1
            
    carData_dict = {'vins': vins, 'years':years, 'makes': makes, 
                 'models': models, 'trims':trims, 'prices': prices,
                 'mileages': mileages, 'cities':cities, 'states': states}
    
    return column_names, carData_dict
 

def data_cleaning(carData_dict):
        
    for column in carData_dict.keys():
        carData_dict[column] = [val if len(val) > 0 
                                else None 
                                for val in carData_dict[column]]
        
    for column in ("years", "prices", "mileages"):
        carData_dict[column] = [int(val) if val is not None and val.isnumeric() 
                                else None 
                                for val in carData_dict[column]]
    
    
    return 0


def print_reports(column_names,carData_dict):
    ncols = len(column_names)
    nRows = len(carData_dict['vins'])
    
    print("\n"+"*"*80)
    print(f"Number of Columns: {ncols}")
    print("-"*80)
    print(f"Number of Rows: {nRows}")
    print("-"*80)
    
    print("*"*80)
    print("columns Names:")
    print("-"*80)
    for indx, item in enumerate(column_names):
        print(indx+1, item)
        
    print("*"*80+"\n")   
    print("Number of empty/invalid Items in Columns of Interest")
    print("-"*80)
    
    for column in carData_dict.keys():
        print(f"{column}: {carData_dict[column].count(None)}")
        print("-"*80)
        
    print("*"*80)
    
    return 0

    

rawDataFile = 'NEWTEST-inventory-listing-2022-08-17.txt'
db_stored_name = "vinaudit_database"
reading_capacity = 1e7
recording_interval = 100000

recording_start =1


column_names, carData_dict = readInfo_fromFile(rawDataFile, reading_capacity)
data_cleaning(carData_dict)
print_reports(column_names,carData_dict)

with connect_to_database() as vinaudit_db:
    create_database(vinaudit_db, db_stored_name)


while recording_start <= reading_capacity:
    recording_end = min(recording_start + recording_interval -1,
                        reading_capacity)
    
    record_range = {"from":recording_start, "to":recording_end}
    
    with connect_to_database() as vinaudit_db:
        insertData_into_database(vinaudit_db, db_stored_name, carData_dict, record_range)
    
    
    recording_start = recording_end +1















    