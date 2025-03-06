from app.database.db import execute_query
from datetime import datetime, timedelta
import logging
import traceback

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_free_subscription():
    # Get the free user ID
    user_result = execute_query('SELECT id FROM users WHERE email = %s', ('free_user@example.com',))
    if not user_result:
        logger.error("Free user not found")
        return False
    
    user_id = user_result[0]['id']
    logger.info(f"Found free user with ID {user_id}")
    
    # Get the Free plan ID
    plan_result = execute_query('SELECT id FROM subscription_plans WHERE name = %s', ('Free',))
    if not plan_result:
        logger.error("Free plan not found")
        return False
    
    plan_id = plan_result[0]['id']
    logger.info(f"Found Free plan with ID {plan_id}")
    
    # Check if subscription already exists
    existing_sub = execute_query(
        'SELECT id FROM user_subscriptions WHERE user_id = %s AND subscription_plan_id = %s AND status = %s',
        (user_id, plan_id, 'active')
    )
    
    if existing_sub:
        logger.info(f"Free user already has an active Free subscription (ID: {existing_sub[0]['id']})")
        return True
    
    # Create subscription
    now = datetime.now()
    end_date = now + timedelta(days=365)  # Free plan for a year
    
    try:
        # Debug: Print the query parameters
        params = (
            user_id, 
            plan_id, 
            f'cus_free_{user_id}', 
            f'sub_free_{user_id}', 
            'active', 
            now, 
            end_date, 
            False
        )
        logger.info(f"Attempting to insert with parameters: {params}")
        
        # Check the table structure
        table_info = execute_query("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'user_subscriptions'")
        logger.info(f"Table structure: {table_info}")
        
        result = execute_query(
            '''
            INSERT INTO user_subscriptions 
            (user_id, subscription_plan_id, stripe_customer_id, stripe_subscription_id, 
             status, current_period_start, current_period_end, cancel_at_period_end) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING id
            ''',
            params
        )
        
        if result:
            subscription_id = result[0]['id']
            logger.info(f"Successfully created Free subscription (ID: {subscription_id}) for free user")
            
            # Verify the subscription was created
            verify = execute_query('SELECT * FROM user_subscriptions WHERE id = %s', (subscription_id,))
            logger.info(f"Verification query result: {verify}")
            
            return True
        else:
            logger.error("Failed to create subscription - no ID returned")
            return False
            
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    add_free_subscription() 