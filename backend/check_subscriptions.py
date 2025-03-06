#!/usr/bin/env python3
"""
Script to check user subscriptions in the database
"""

from database.db import execute_query

def main():
    print("User subscriptions in database:")
    subscriptions = execute_query('''
        SELECT us.id, u.email, sp.name as plan_name, us.status, us.current_period_end
        FROM user_subscriptions us
        JOIN users u ON us.user_id = u.id
        JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
    ''')
    
    if not subscriptions:
        print("No user subscriptions found in the database.")
        return
    
    for sub in subscriptions:
        print(f'ID: {sub["id"]}, User: {sub["email"]}, Plan: {sub["plan_name"]}, Status: {sub["status"]}, Expires: {sub["current_period_end"]}')

if __name__ == "__main__":
    main() 