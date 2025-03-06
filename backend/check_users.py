#!/usr/bin/env python3
"""
Script to check users in the database
"""

from database.db import execute_query

def main():
    print("Users in database:")
    users = execute_query('SELECT id, email, full_name FROM users')
    
    if not users:
        print("No users found in the database.")
        return
    
    for user in users:
        print(f'ID: {user["id"]}, Email: {user["email"]}, Name: {user["full_name"]}')
    
    print("\nSubscription plans:")
    plans = execute_query('SELECT id, name FROM subscription_plans')
    
    if not plans:
        print("No subscription plans found in the database.")
        return
    
    for plan in plans:
        print(f'ID: {plan["id"]}, Name: {plan["name"]}')

if __name__ == "__main__":
    main() 