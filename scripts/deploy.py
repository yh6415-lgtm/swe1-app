"""Deploy coursework with AWS CLI authentication and the EB CLI.

Creates one t3.micro instance, EB roles and an SSH key. Run only after signing
in to your personal AWS account and checking its Free Tier plan/credits.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

from package import ROOT, build_package


class Aws:
    def __init__(self, region, profile):
        self.region = region
        self.profile = profile

    def call(self, *args, missing=None):
        result = subprocess.run([
            "aws", *args, "--region", self.region, "--profile", self.profile,
            "--output", "json", "--no-cli-pager",
        ], capture_output=True, text=True, encoding="utf-8")
        if result.returncode:
            if missing and f"({missing})" in result.stderr:
                return None
            # Never print command arguments: some AWS calls contain credentials.
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def ensure_role(self, name, service, policies):
        if self.call("iam", "get-role", "--role-name", name, missing="NoSuchEntity") is None:
            statement = {
                "Effect": "Allow", "Principal": {"Service": service},
                "Action": "sts:AssumeRole",
            }
            if service == "elasticbeanstalk.amazonaws.com":
                statement["Condition"] = {"StringEquals": {"sts:ExternalId": "elasticbeanstalk"}}
            trust = {"Version": "2012-10-17", "Statement": [statement]}
            self.call("iam", "create-role", "--role-name", name,
                      "--assume-role-policy-document", json.dumps(trust))
        for policy in policies:
            self.call("iam", "attach-role-policy", "--role-name", name,
                      "--policy-arn", "arn:aws:iam::aws:policy/" + policy)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--environment", help="Default: swe1-app-ACCOUNT_ID")
    args = parser.parse_args()
    if not shutil.which("aws"):
        raise RuntimeError("Install AWS CLI v2 first.")
    aws = Aws(args.region, args.profile)
    identity = aws.call("sts", "get-caller-identity")
    name = args.environment or "swe1-app-" + identity["Account"]
    print(f"AWS account: {identity['Account']}; region: {args.region}; environment: {name}", flush=True)

    eb_python = ROOT / ".ebcli-venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not eb_python.exists():
        raise RuntimeError("Install the isolated EB CLI as described in DEPLOYMENT.md.")
    # AWS CLI login credentials are also usable with older EB CLI SDK versions.
    credentials = aws.call("configure", "export-credentials", "--format", "process")
    eb_environment = {
        **os.environ,
        "AWS_ACCESS_KEY_ID": credentials["AccessKeyId"],
        "AWS_SECRET_ACCESS_KEY": credentials["SecretAccessKey"],
        "AWS_SESSION_TOKEN": credentials.get("SessionToken", ""),
        "AWS_DEFAULT_REGION": args.region,
    }

    def eb(*arguments):
        result = subprocess.run([str(eb_python), "-m", "ebcli", *arguments],
                                cwd=ROOT, env=eb_environment)
        if result.returncode:
            raise RuntimeError("EB CLI failed. Inspect its messages or run eb logs.")

    existing = aws.call("elasticbeanstalk", "describe-environments",
                        "--application-name", "swe1-app", "--environment-names", name)["Environments"]
    if existing and existing[0]["Status"] != "Ready":
        raise RuntimeError(f"Environment status is {existing[0]['Status']}; wait or inspect EB events before retrying.")
    if existing:
        stack = existing[0]["SolutionStackName"]
        hostname = existing[0]["CNAME"]
    else:
        stacks = aws.call("elasticbeanstalk", "list-available-solution-stacks")["SolutionStacks"]
        stack = next((value for value in stacks if "Amazon Linux 2023" in value and "Python 3.12" in value), None)
        if not stack:
            raise RuntimeError("No supported Python 3.12 / Amazon Linux 2023 platform in this region.")
        dns = aws.call("elasticbeanstalk", "check-dns-availability", "--cname-prefix", name)
        if not dns["Available"]:
            raise RuntimeError("CNAME is taken. Pass a different --environment name.")
        hostname = dns["FullyQualifiedCNAME"]
        service_role = "swe1-app-eb-service-role"
        instance_role = "swe1-app-eb-ec2-role"
        aws.ensure_role(service_role, "elasticbeanstalk.amazonaws.com", [
            "AWSElasticBeanstalkEnhancedHealth", "AWSElasticBeanstalkManagedUpdatesCustomerRolePolicy",
        ])
        aws.ensure_role(instance_role, "ec2.amazonaws.com", ["AWSElasticBeanstalkWebTier"])
        profile = aws.call("iam", "get-instance-profile", "--instance-profile-name", instance_role, missing="NoSuchEntity")
        if profile is None:
            profile = aws.call("iam", "create-instance-profile", "--instance-profile-name", instance_role)
        if not any(role["RoleName"] == instance_role for role in profile["InstanceProfile"]["Roles"]):
            aws.call("iam", "add-role-to-instance-profile", "--instance-profile-name", instance_role,
                     "--role-name", instance_role)
        vpcs = aws.call("ec2", "describe-vpcs", "--filters", "Name=is-default,Values=true")["Vpcs"]
        if not vpcs:
            print("Creating the default VPC required by the course instructions.", flush=True)
            aws.call("ec2", "create-default-vpc")
        ssh_directory = Path.home() / ".ssh"
        ssh_directory.mkdir(exist_ok=True)
        keyname = name + "-" + args.region
        keyfile = ssh_directory / (keyname + ".pem")
        pairs = aws.call("ec2", "describe-key-pairs", "--key-names", keyname,
                         missing="InvalidKeyPair.NotFound")
        if pairs is None:
            if keyfile.exists():
                raise RuntimeError("Local SSH key exists without the matching AWS key; select a new environment name.")
            key = aws.call("ec2", "create-key-pair", "--key-name", keyname, "--key-type", "rsa")
            descriptor = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                stream.write(key["KeyMaterial"])
        elif not keyfile.exists():
            raise RuntimeError("The AWS SSH key exists but its local private key is missing; select a new environment name.")
        # Give IAM time to propagate before EB requests EC2 instances.
        time.sleep(10)

    build_package()
    eb("init", "swe1-app", "--platform", stack, "--region", args.region)
    # Deploy exactly the reviewed ZIP; it excludes databases, credentials and tools.
    config = ROOT / ".elasticbeanstalk" / "config.yml"
    configure_artifact = (
        "import pathlib, sys, yaml; p=pathlib.Path(sys.argv[1]); "
        "c=yaml.safe_load(p.read_text()) or {}; "
        "c['deploy']={'artifact':'dist/swe1-app.zip'}; "
        "p.write_text(yaml.safe_dump(c,sort_keys=False))"
    )
    subprocess.run([str(eb_python), "-c", configure_artifact, str(config)], check=True)
    if existing:
        eb("deploy", name, "--timeout", "20")
    else:
        eb("create", name, "--single", "--instance_type", "t3.micro", "--cname", name,
           "--service-role", service_role, "--instance_profile", instance_role,
           "--keyname", keyname, "--envvars", f"DJANGO_ALLOWED_HOSTS={hostname};localhost;127.0.0.1",
           "--timeout", "20")
    details = aws.call("elasticbeanstalk", "describe-environments", "--environment-names", name)["Environments"][0]
    url = "http://" + details["CNAME"] + "/polls/"
    print(f"Verifying {url}", flush=True)
    with urllib.request.urlopen(url, timeout=30) as response:
        html = response.read().decode()
        if response.status != 200 or "Latest polls" not in html or "No polls are available." in html:
            raise RuntimeError("The deployed polls index did not pass the HTTP check.")
    submission = ROOT / "SUBMISSION.md"
    submission.write_text(
        "# Brightspace submission\n\n"
        f"Django application: {url}\n\n"
        "GitHub repository: https://github.com/yuelihe2-svg/swe1-app\n\n"
        "Before submitting, open the application in an incognito browser, vote, and check the results.\n"
        "Keep the environment running until grading is complete.\n", encoding="utf-8",
    )
    print(f"Deployment passed. Submission links saved to {submission}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
