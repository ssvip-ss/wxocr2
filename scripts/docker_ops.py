import subprocess
import sys


def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    # Build the Docker image
    print("Building Docker image...")
    run_command("docker build -t wxocr .")

    # Run the Docker container
    print("Starting Docker container...")
    run_command("docker run --rm -p 5000:5000 wxocr")


if __name__ == "__main__":
    main()
