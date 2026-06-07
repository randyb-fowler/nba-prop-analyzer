import sys
from src.nba_stats import find_player, fetch_game_log, display


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py \"Player Name\"")
        sys.exit(1)

    name = " ".join(sys.argv[1:])

    try:
        player = find_player(name)
        print(f"Found: {player['full_name']} (ID {player['id']})")
        game_log = fetch_game_log(player["id"])
        display(player["full_name"], game_log)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
