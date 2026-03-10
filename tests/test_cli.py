import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cli.parser import create_parser

def test_run_command_parsing():
    parser = create_parser()
    args = parser.parse_args(["run", "project-update", "--target", "file.py", "--goal", "refactor"])
    assert args.command == "run"
    assert args.workflow == "project-update"
    assert args.target == "file.py"
    assert args.goal == "refactor"

def test_missing_run_args():
    parser = create_parser()
    with pytest.raises(SystemExit):
        # run requires a workflow argument
        parser.parse_args(["run"])

def test_doctor_cmd():
    parser = create_parser()
    args = parser.parse_args(["doctor"])
    assert args.command == "doctor"
    
def test_workflows_list_cmd():
    parser = create_parser()
    args = parser.parse_args(["workflows", "list"])
    assert args.command == "workflows"
    assert args.subcommand == "list"
    
def test_memory_show_cmd():
    parser = create_parser()
    args = parser.parse_args(["memory", "show"])
    assert args.command == "memory"
    assert args.subcommand == "show"
