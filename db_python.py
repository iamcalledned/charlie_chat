import mysql.connector
from config import Config

def drop_tables(cursor):
    tables = ["ingredients", "instructions", "recipes", "threads", "conversations", "user_data", "verifier_store"]
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")
            print(f"Dropped table {table}")
        except mysql.connector.Error as err:
            print(f"Error: {err}")

def create_tables(cursor):
    user_data = """
        CREATE TABLE user_data (
            userID int NOT NULL AUTO_INCREMENT,
            username varchar(255) NOT NULL UNIQUE,
            email varchar(255),
            name varchar(255),
            setup_date datetime,
            last_login_date datetime,
            current_session_id varchar(48),
            PRIMARY KEY (userID)
        );
    """
 
    recipes = """
        CREATE TABLE recipes (
            recipe_id INT AUTO_INCREMENT PRIMARY KEY,
            userID INT,
            title VARCHAR(255) NOT NULL,
            servings VARCHAR(255),
            prep_time VARCHAR(255),
            cook_time VARCHAR(255),
            total_time VARCHAR(255),
            FOREIGN KEY (userID) REFERENCES user_data(userID)
        );
    """
    
    ingredients =  """
        CREATE TABLE ingredients (
            ingredient_id INT AUTO_INCREMENT PRIMARY KEY,
            recipe_id INT,
            item VARCHAR(255) NOT NULL,
            category VARCHAR(255),
            FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id)
        );
        """
    instructions = """
        CREATE TABLE instructions (
            instruction_id INT AUTO_INCREMENT PRIMARY KEY,
            recipe_id INT,
            step_number INT,
            description TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id)
        );
        """
    conversations = """
        CREATE TABLE conversations (
            ConversationID int NOT NULL AUTO_INCREMENT,
            userID int NOT NULL,
            threadID varchar(36) NOT NULL,
            RunID varchar(36) NOT NULL,
            Message text NOT NULL,
            Timestamp datetime DEFAULT CURRENT_TIMESTAMP,
            MessageType varchar(255) NOT NULL,
            IPAddress varchar(255),
            Status varchar(255) DEFAULT 'active',
            PRIMARY KEY (ConversationID),
            FOREIGN KEY (userID) REFERENCES user_data(userID)
        );
    """

    threads = """
        CREATE TABLE threads (
            threadID varchar(36) NOT NULL,
            userID int NOT NULL,
            IsActive tinyint(1) NOT NULL,
            CreatedTime datetime NOT NULL,
            PRIMARY KEY (threadID),
            FOREIGN KEY (userID) REFERENCES user_data(userID)
        );
    """

    verifier_store = """
        CREATE TABLE verifier_store (
            state varchar(255) NOT NULL,
            code_verifier varchar(255) NOT NULL,
            client_ip varchar(15),
            login_timestamp timestamp,
            PRIMARY KEY (state)
        );
    """

    

    table_creation_queries = [user_data, recipes, ingredients, instructions, conversations, threads, verifier_store]

    for query in table_creation_queries:
        try:
            cursor.execute(query)
            print("Table created successfully")
        except mysql.connector.Error as err:
            print(f"Error: {err}")

def main():
    db_config = {
        'host': Config.DB_HOST,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
        'database': Config.DB_NAME
    }

    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        drop_tables(cursor)
        create_tables(cursor)
        connection.commit()
        print("Database setup completed successfully.")
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    main()
