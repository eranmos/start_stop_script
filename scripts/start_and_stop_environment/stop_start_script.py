
import boto3
import time
import sys
import logging

TAG_KEY = 'Environment Name'
TAG_VALUE = sys.argv[1]
SCHEDULE_TAG_KEY = "startstop-schedule"
ORIG_SCHEDULE_TAG_VALUE = f'{TAG_VALUE.lower()}-server'
NEW_SCHEDULE_TAG_VALUE = "stop_start_by_pipeline_manually"
ENVIRONMENT_STOP_START= sys.argv[2]
DB_IDENTIFIER = f'sqlrdsdb-{TAG_VALUE.lower()}'

# Set the logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#######################################################################################
############## List AWS EC2 Instance ##############
def list_instances_by_tag(tag_key, tag_value):
    # Create an EC2 client object
    ec2_client = boto3.client('ec2')

    # Call the describe_instances() method with the filter
    response = ec2_client.describe_instances(Filters=[{'Name': f'tag:{tag_key}', 'Values': [tag_value]}])

    # Loop through the list of instances and print their details
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_state = instance['State']['Name']
            logging.info(f"Instance ID: {instance_id}, State: {instance_state}")

#######################################################################################
############## Update Tag AWS EC2 Instance ##############
def update_tag_value_by_tag(tag_key, tag_value, new_tag_value):
    # Create an EC2 client object
    ec2_client = boto3.client('ec2')

    # Get the instance IDs based on the tag filter
    response = ec2_client.describe_instances(Filters=[{'Name': f'tag:{tag_key}', 'Values': [tag_value]}])

    # Extract the instance IDs
    instance_ids = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])

    # Update the tag value for each instance
    if instance_ids:
        ec2_client.create_tags(Resources=instance_ids, Tags=[{'Key': tag_key, 'Value': new_tag_value}])
        logging.info(f"Updated tag value for instances with tag {tag_key}={tag_value}")
    else:
        logging.info(f"No instances found with tag {tag_key}={tag_value}")

#######################################################################################
############## Start AWS EC2 Instance ##############
def start_instances_by_tag(tag_key, tag_value):
    # Create an EC2 client object
    ec2_client = boto3.client('ec2')

    # Get the instances with the specified tag
    response = ec2_client.describe_instances(Filters=[{'Name': f'tag:{tag_key}', 'Values': [tag_value]}])

    # Loop through the instances and start them one by one
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_state = instance['State']['Name']

            if instance_state != 'running':
                # Check if the instance is not already running
                logging.info(f"Starting instance: {instance_id}")

                # Start the instance
                ec2_client.start_instances(InstanceIds=[instance_id])

                # Wait until the instance is running
                while True:
                    response = ec2_client.describe_instances(InstanceIds=[instance_id])
                    instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
                    if instance_state == 'running':
                        break
                    t = time.localtime()
                    current_time = time.strftime("%H:%M:%S", t)
                    time.sleep(20)  # Wait for 5 seconds before checking again

                logging.info(f"Instance started: {instance_id}")
            else:
                logging.info(f"Instance already running: {instance_id}")

#######################################################################################
############## Stop AWS EC2 Instance ##############
def stop_instances_by_tag(tag_key, tag_value):
    # Create an EC2 client object
    ec2_client = boto3.client('ec2')

    # Get the instances based on the tag filter
    response = ec2_client.describe_instances(Filters=[{'Name': f'tag:{tag_key}', 'Values': [tag_value]}])

    # Iterate through the instances and stop them one by one
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_state = instance['State']['Name']

            # Check if the instance is in a running state
            if instance_state == 'running':
                logging.info(f"Stopping instance with ID: {instance_id}")
                ec2_client.stop_instances(InstanceIds=[instance_id])

                # Wait until the instance is stopped
                while True:
                    response = ec2_client.describe_instances(InstanceIds=[instance_id])
                    instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
                    if instance_state == 'stopped':
                        logging.info(f"Instance with ID {instance_id} stopped successfully")
                        break
                    else:
                        t = time.localtime()
                        current_time = time.strftime("%H:%M:%S", t)
                        logging.info(f"Waiting for the instance to stop...")
                        time.sleep(10)
            else:
                logging.info(f"Instance with ID {instance_id} is not in a running state, skipping...")

#######################################################################################
############## Start AWS RDS ##############
def start_rds_instances(db_identifier):
    # Create an RDS client object
    rds_client = boto3.client('rds')

    # Describe the RDS instance
    response = rds_client.describe_db_instances(DBInstanceIdentifier=db_identifier)

    # Get the status of the RDS instance
    instance_status = response['DBInstances'][0]['DBInstanceStatus']

    if instance_status == 'available':
        logging.info(f"RDS instance {db_identifier} is already up and running.")
    else:
        logging.info(f"RDS instance {db_identifier} is not available. Starting the instance...")

        # Start the RDS instance
        rds_client.start_db_instance(DBInstanceIdentifier=db_identifier)

        # Wait until the instance is available
        while True:
            response = rds_client.describe_db_instances(DBInstanceIdentifier=db_identifier)
            instance_status = response['DBInstances'][0]['DBInstanceStatus']
            if instance_status == 'available':
                logging.info(f"RDS instance {db_identifier} is now up and running.")
                break
            else:
                logging.info(f"Waiting for the RDS instance to become available...")
                time.sleep(300)

########################################################################################
############## Stop AWS RDS ##############
def stop_rds_instances(db_identifier):
    # Create an RDS client object
    rds_client = boto3.client('rds')

    # Describe the RDS instances based on the provided DB identifier
    response = rds_client.describe_db_instances(DBInstanceIdentifier=db_identifier)

    # Iterate through the instances and stop them
    for db_instance in response['DBInstances']:
        instance_id = db_instance['DBInstanceIdentifier']
        instance_status = db_instance['DBInstanceStatus']

        # Check if the instance is in a running state
        if instance_status == 'available':
            logging.info(f"Stopping RDS instance with DB identifier: {instance_id}")
            rds_client.stop_db_instance(DBInstanceIdentifier=db_identifier)

            # Wait until the instance is stopped
            while True:
                response = rds_client.describe_db_instances(DBInstanceIdentifier=db_identifier)
                instance_status = response['DBInstances'][0]['DBInstanceStatus']
                if instance_status == 'stopped':
                    logging.info(f"RDS instance with DB identifier {instance_id} stopped successfully")
                    break
                else:
                    t = time.localtime()
                    current_time = time.strftime("%H:%M:%S", t)
                    logging.info(f"Waiting for the RDS instance to stop...")
                    time.sleep(60)
        else:
            logging.info(f"RDS instance with DB identifier {instance_id} is not in a running state, skipping...")

########################################################################################
############## Retag AWS RDS ##############
def retag_rds_instances(db_identifier, tags):
    # Create an RDS client object
    rds_client = boto3.client('rds')

    # Add or update the tags for the RDS instance
    response = rds_client.add_tags_to_resource(ResourceName=f"arn:aws:rds:ap-southeast-2:863128883465:db:{db_identifier}", Tags=tags)
    logging.info(f"Retagged RDS instance with DB identifier: {db_identifier}")

########################################################################################

if ENVIRONMENT_STOP_START == 'start':
    # Starting AWS RDS
    start_rds_instances(DB_IDENTIFIER)
    logging.info(f'Going to ReTAG AWS RDS: {DB_IDENTIFIER}')
    retag_rds_instances(DB_IDENTIFIER, tags=[{'Key': f'{SCHEDULE_TAG_KEY}', 'Value': f'{NEW_SCHEDULE_TAG_VALUE}'}])

    # Starting AWS EC2 Instances
    logging.info(f"The servers list in {TAG_VALUE} environment are:")
    list_instances_by_tag(TAG_KEY, TAG_VALUE)
    logging.info(f"Going to start servers in {TAG_VALUE} environment")
    start_instances_by_tag(TAG_KEY, TAG_VALUE)
    logging.info(f"Going to retag servers in {TAG_VALUE} environment")
    update_tag_value_by_tag(SCHEDULE_TAG_KEY, ORIG_SCHEDULE_TAG_VALUE, NEW_SCHEDULE_TAG_VALUE)

elif ENVIRONMENT_STOP_START == 'stop':
    # Stopping AWS RDS
    logging.info(f'Going to stop AWS RDS: {DB_IDENTIFIER}')
    stop_rds_instances(DB_IDENTIFIER)
    logging.info(f'Going to ReTAG AWS RDS: {DB_IDENTIFIER}')
    retag_rds_instances(DB_IDENTIFIER, tags=[{'Key': f'{SCHEDULE_TAG_KEY}', 'Value': f'{NEW_SCHEDULE_TAG_VALUE}'}])

    # Stopping AWS EC2 Instances
    logging.info(f"The servers list in {TAG_VALUE} environment are:")
    list_instances_by_tag(TAG_KEY, TAG_VALUE)
    logging.info(f"Going to stop servers in {TAG_VALUE} environment")
    stop_instances_by_tag(TAG_KEY,TAG_VALUE)
    logging.info(f"Going to retag servers in {TAG_VALUE} environment")
    update_tag_value_by_tag(SCHEDULE_TAG_KEY, ORIG_SCHEDULE_TAG_VALUE, NEW_SCHEDULE_TAG_VALUE)

else:
    logging.info("Please choose the right parameter 'stop' or 'start' the environment ")
