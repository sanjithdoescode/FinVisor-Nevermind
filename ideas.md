# ideas

## Simulator API:

- a service should be actively sending live transaction data consisting of the amount spent, type of expense, time, date, account balance 

- this live data will be used to analyze everything. from identifying unusual spending, recurring/hidden costs, and budget violations, and generating a financial plan grounded in the actual numbers

- use redis for live data

# plan

to create an agent who is able to process live transaction data to identify unusual spending, recurring/hidden costs, and budget violations, then generates a financial plan grounded in the actual numbers — not generic tips.

check out problem_statement.md for more details and perform your own research based on the given info about the project.


# Small Business - Target Audience

- our target audience are small enterprises.
- there are two things to consider here:
  - Good transaction
  - Bad Transaction 
- How do we classify something as good transaction and something as bad transaction?:
  - Good transaction yields profit for the business owner
  - Bad transaction yields loss for the business owner
- Example:
  - For a retailer, there are two modes of cash flow:
    - Order ("Debit")
    - Sales ("Credit")
  - A bad transaction happens when an ordered item is not being sold for a long time and is kept idle in the inventory
  - A good transaction happens when an ordered item is sold as soon as possible and spends minimal time in the inventory

- We now follow this logic for all sorts of businesses 

