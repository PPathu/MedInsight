from app.query import execute_sql_query

# Define a sample query that you want Qwen to generate SQL for.
sample_query = "SELECT drug, starttime, stoptime FROM prescriptions WHERE subject_id = 10000032;"

# Call the function that sends the query to Qwen
generated_sql = execute_sql_query(sample_query)

# Print out the generated SQL
print("Generated SQL Query:")
print(generated_sql)
