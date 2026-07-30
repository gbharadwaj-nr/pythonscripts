import boto3
import os      
import sys
from botocore.exceptions import ClientError

# =============================================================================
# CONFIGURATION
# =============================================================================

ROLE_NAME = "FinOpsAutomationRole"

CLIENTS = {
    "1": {"client_name": "ATB", "region": "NA", "account_id": "578236091839"},
    "2": {"client_name": "Bank of Queensland (BoQ)", "region": "APAC", "account_id": "340333144889"},
    "3": {"client_name": "BHFS", "region": "EMEA", "account_id": "476149950471"},
    "4": {"client_name": "Coop", "region": "EMEA", "account_id": "450683977817"},
    "5": {"client_name": "Equifax", "region": "EMEA", "account_id": "386062453979"},
    "6": {"client_name": "FleetCor", "region": "NA", "account_id": "444521715692"},
    "7": {"client_name": "Generali", "region": "EMEA", "account_id": "078988040627"},
    "8": {"client_name": "IAG", "region": "APAC", "account_id": "402366105298"},
    "9": {"client_name": "Latitude (LFS)", "region": "APAC", "account_id": "616476889381"},
    "10": {"client_name": "Macquarie (MGL)", "region": "APAC", "account_id": "984546913585"},
    "11": {"client_name": "Mizuho", "region": "EMEA", "account_id": "425998559800"},
    "12": {"client_name": "NationWide (NBS)", "region": "EMEA", "account_id": "720186310367"},
    "13": {"client_name": "Suncorp", "region": "APAC", "account_id": "889716922160"},
    "14": {"client_name": "TabCorp", "region": "APAC", "account_id": "590183781567"},
}

# =============================================================================
# MENU
# =============================================================================

def show_menu():

    print("\n" + "=" * 90)
    print("AWS DAILY HEALTH CHECK")
    print("=" * 90)

    print(f"{'No':<5}{'Client':<35}{'Business Region'}")
    print("-" * 90)

    for key, value in CLIENTS.items():
        print(f"{key:<5}{value['client_name']:<35}{value['region']}")

    choice = input("\nSelect Client Number : ").strip()

    if choice not in CLIENTS:
        print("Invalid selection.")
        sys.exit(1)

    return CLIENTS[choice]

def get_account_by_name(client_name):

    for account in CLIENTS.values():

        if account["client_name"].lower() == client_name.lower():
            return account

        # Support short names used in Jenkins
        aliases = {
            "BOQ": "Bank of Queensland (BoQ)",
            "MGL": "Macquarie (MGL)",
            "LFS": "Latitude (LFS)",
            "BHFS": "BHFS",
            "ATB": "ATB",
            "COOP": "Coop",
            "EQUIFAX": "Equifax",
            "FLEETCOR": "FleetCor",
            "GENERALI": "Generali",
            "IAG": "IAG",
            "MIZUHO": "Mizuho",
            "NBS": "NationWide (NBS)",
            "SUNCORP": "Suncorp",
            "TABCORP": "TabCorp"
        }

    if client_name.upper() in aliases:

        actual_name = aliases[client_name.upper()]

        for account in CLIENTS.values():
            if account["client_name"] == actual_name:
                return account

    return None

# =============================================================================
# ASSUME ROLE
# =============================================================================

def assume_role(account):

    sts = boto3.client("sts")

    role_arn = f"arn:aws:iam::{account['account_id']}:role/{ROLE_NAME}"

    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="HealthCheckSession"
    )

    creds = response["Credentials"]

    session = boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"]
    )

    return session

# =============================================================================
# REGION DISCOVERY
# =============================================================================

def discover_regions(session):

    ec2 = session.client("ec2", region_name="us-east-1")

    all_regions = [r["RegionName"] for r in ec2.describe_regions()["Regions"]]

    active_regions = []

    for region in all_regions:

        ec2 = session.client("ec2", region_name=region)

        instances = ec2.describe_instances()

        has_instances = any(
            reservation["Instances"]
            for reservation in instances["Reservations"]
        )

        if has_instances:
            active_regions.append(region)

    return active_regions

# =============================================================================
# EC2 CHECK
# =============================================================================

def check_ec2(session, regions):

    total_running = 0
    total_stopped = 0

    print("\n")
    print("=" * 140)
    print("EC2 INVENTORY")
    print("=" * 140)

    print(
        f"{'Region':18}"
        f"{'Instance Name':30}"
        f"{'Instance ID':22}"
        f"{'Type':15}"
        f"{'State':12}"
        f"{'Private IP':18}"
    )

    print("-" * 140)

    for region in regions:

        ec2 = session.client("ec2", region_name=region)

        try:

            reservations = ec2.describe_instances()["Reservations"]

        except Exception:
            continue

        if not reservations:
            continue

        status_lookup = {}

        try:
            statuses = ec2.describe_instance_status(
                IncludeAllInstances=True
            )["InstanceStatuses"]

            for s in statuses:
                status_lookup[s["InstanceId"]] = {
                    "system": s["SystemStatus"]["Status"],
                    "instance": s["InstanceStatus"]["Status"]
                }

        except Exception:
            pass

        for reservation in reservations:

            for instance in reservation["Instances"]:

                state = instance["State"]["Name"]

                if state == "running":
                    total_running += 1
                else:
                    total_stopped += 1

                instance_name = "N/A"

                if "Tags" in instance:
                    for tag in instance["Tags"]:
                        if tag["Key"] == "Name":
                            instance_name = tag["Value"]

                private_ip = instance.get("PrivateIpAddress", "-")

                instance_type = instance["InstanceType"]

                system_status = "-"
                instance_status = "-"

                if instance["InstanceId"] in status_lookup:

                    system_status = status_lookup[instance["InstanceId"]]["system"]

                    instance_status = status_lookup[instance["InstanceId"]]["instance"]

                print(
                    f"{region:18}"
                    f"{instance_name[:28]:30}"
                    f"{instance['InstanceId']:22}"
                    f"{instance_type:15}"
                    f"{state:12}"
                    f"{private_ip:18}"
                )

                print(
                    f"{'':18}"
                    f"System Status   : {system_status} | Instance Status : {instance_status}"
                )

    print("\n" + "=" * 70)
    print("EC2 SUMMARY")
    print("=" * 70)

    print(f"Running Instances : {total_running}")
    print(f"Stopped Instances : {total_stopped}")
    print(f"Total Instances   : {total_running + total_stopped}")

# =============================================================================
# MAIN
# =============================================================================

def main():

    # ---------------------------------------------------------
    # Check if running from Jenkins
    # ---------------------------------------------------------

    selected_client = os.getenv("CLIENT")

    # ---------------------------------------------------------
    # If Jenkins parameter exists
    # ---------------------------------------------------------

    if selected_client:

        print("\nRunning from Jenkins")
        print("-----------------------------")
        print(f"Selected Client : {selected_client}")

        account = get_account_by_name(selected_client)

        if account is None:
            print("Invalid CLIENT parameter.")
            sys.exit(1)

    # ---------------------------------------------------------
    # Otherwise run locally
    # ---------------------------------------------------------

    else:

        account = show_menu()

    print("\nSelected Client")
    print("-" * 50)

    print(f"Client Name : {account['client_name']}")
    print(f"Account ID  : {account['account_id']}")

    print("\nAssuming Role...")

    try:

        session = assume_role(account)

        print("SUCCESS")

    except ClientError as e:

        print("FAILED")
        print(e)
        sys.exit(1)

    print("\nDiscovering AWS Regions...\n")

    regions = discover_regions(session)

    for region in regions:
        print(f"[OK] {region}")

    print(f"\nTotal Regions : {len(regions)}")

    check_ec2(session, regions)


if __name__ == "__main__":
    main()