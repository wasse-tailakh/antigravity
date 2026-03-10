import sys
from cli.parser import create_parser
from cli.commands import handle_run, handle_workflows, handle_memory, handle_runs, handle_doctor
from cli.formatters import print_banner

def main_runner():
    print_banner()
    
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command == "run":
        handle_run(args)
    elif args.command == "workflows":
        handle_workflows(args)
    elif args.command == "memory":
        handle_memory(args)
    elif args.command == "runs":
        handle_runs(args)
    elif args.command == "doctor":
        handle_doctor(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main_runner()
