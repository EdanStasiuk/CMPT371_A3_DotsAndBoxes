# CMPT371_A3_DotsAndBoxes
Assignment 3
Course: CMPT 371 - Data Communications & Networking  
Instructor: Mirza Zaeem Baig  
Semester: Spring 2026  

--------------------------------------------------

## 👥 Group Members

| Name | Student ID | Email |
|------|------------|-------|
| **Edan Stasiuk** | 301450211 | [edan_stasiuk@sfu.ca](mailto:edan_stasiuk@sfu.ca) |
| **Noah Vattathichirayil** | 301548329 | [nva16@sfu.ca](mailto:nva16@sfu.ca) |

--------------------------------------------------

## 1. Project Overview & Description

This project is a multiplayer Dots and Boxes game built using Python's Socket API (TCP). It allows two distinct clients to connect to a central server, be matched into a game session, and play against each other in real-time.

The server is responsible for:
- Maintaining the game board (grid of dots and lines)
- Validating moves
- Detecting completed boxes
- Updating scores
- Enforcing turn-based gameplay

This ensures that clients cannot cheat by modifying their local game state.

The game itself is called Dots and Boxes. How the game is played, is that players take turns putting edges between the dots on screen, and when a box is created, that box is awarded as a point to the player that placed the last edge to create that box. If a box is created by a player, they get to take another turn. Player wins if they have more boxes than the other by the time the entire grid is filled with claimed boxes.

--------------------------------------------------

## 2. System Limitations & Edge Cases

Exactly Two Players Required:

Limitation: The server does not support spectators, reconnection, or more than 2 players. If a third client attempts to connect after the game starts, it will be left hanging with no response, as the server stops accepting new connections once the game begins.
Solution: The server explicitly waits for exactly 2 TCP connections before starting the game. Once both players are connected, the server broadcasts a start message and begins handling moves.

--------------------------------------------------

Single Game Per Server Instance:

Limitation: The server manages exactly one game session per run. Once the game ends (or a player disconnects), the server process exits. To play another game, both the server and both clients must be restarted manually.
Solution: Implementation that would loop back to the lobby and accept new connections after each game concludes.

--------------------------------------------------

Fixed Grid Size:

Limitation: The grid size (default 4×4) is hardcoded in server.py via the GRID_SIZE constant and cannot be changed once the server is running. Players cannot select a board size. Changing the grid size requires editing the constant and restarting the server before any clients connect.
Solution: Make an option for different grid sizes before game start

--------------------------------------------------

## 3. Video Demo

Our 2-minute video demonstration covering connection establishment, data exchange, real-time gameplay, and game completion can be viewed below:

Watch Project Demo on YouTube

https://youtu.be/gsqeIgZTMPE

--------------------------------------------------

## 4. Prerequisites (Fresh Environment)

To run this project, you need:

- Python 3.10 or higher
- Libraries in the "requirements.txt" file (explicit instructions given on how to download)
- (Optional) VS Code or Terminal

--------------------------------------------------

## 5. Step-by-Step Run Guide

---

### Step 1: Clone repository to your own machine

Clone the Repository to your own machine using the git

```bash
git clone https://github.com/EdanStasiuk/CMPT371_A3_DotsAndBoxes.git
```

---

### Step 2: Create Virtual Environment

Make sure you are in the correct project directory and then use the following commands in a terminal
to create a virtual environment
(This is to install the packages into locally without poluting global package space)

```bash
# Create venv
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install necessary libraries
pip install -r requirements.txt
```

---

### Step 3: Starting the Server

On a terminal start the server using the below command

```bash
python3 server.py
```

---

### Step 4: Connect Player 1

Open a new terminal window (keep the server running). Run the gui.py script to start the first client.

```bash
python3 gui.py
```

#### Troubleshooting:

If you receive the following error:

```bash
ModuleNotFoundError: No module named 'pygame'
```

This usually means your terminal is using the system's Python instead of the one in your virtual environment (common if `python3` is aliased to a global version).

Quick Fix: Run the script by pointing directly to the virtual environment’s Python binary:

```bash
./venv/bin/python3 gui.py
```

---

### Step 3: Connect Player 2

Open a third terminal window. Run the gui.py script again to start the second client.

```bash
python3 gui.py
```

---

### Step 4: Gameplay

1. Players take turns drawing lines between adjacent dots.

2. When prompted, hover over where you would like to place a line, and click.

3. Players take turns placing lines, completing boxes as they go.

The server will:
   - Update the board on both clients  
   - Check for completed boxes  
   - Update scores  

If a player completes a box:
   - They earn a point  
   - They get another turn  

4. The game ends when all boxes are completed, and the winner is announced. Windows can be closed by both players, disconnecting from server.

--------------------------------------------------

## 6. Technical Protocol Details (JSON over TCP)

### Message Format:
```json
{
   "type": "<string>",
   "...": "additional fields depending on type"
}
```

--------------------------------------------------

### Connection & Assignment Phase:

Server sends to client:
```json
{
   "type": "assign",
   "player": 1,
   "grid_size": 4
}
```

- Sent immediately after connection
- Assigns player number (1 or 2)
- Provides grid size

--------------------------------------------------

### Game Start:

Server broadcasts to all clients:
```json
{
   "type": "start",
   "state": { ... }
}
```

- Sent once both players are connected
- Includes full initial game state

--------------------------------------------------

### Gameplay Phase:

Clients sends to 
```json
{
   "type": "move",
   "move": {
     "orientation": "H",
     "row": 1,
     "col": 1
   }
}
```

- `orientation`: `"H"` (horizontal) or `"V"` (vertical)
- `row`, `col`: edge coordinates

Server broadcasts to all clients (State Update)
```json
{
   "type": "state_update",
   "state": { ... }
}
```

- Broadcast after every valid move
- `state` includes:
   - Board representation
   - Scores
   - Current turn (`current_turn`)
   - Any other game metadata

--------------------------------------------------

### Error Handling:

Server sends to client:
```json
{
   "type": "error",
   "message": "It's not your turn."
}
```

Examples:
- Invalid move (edge already drawn)
- Wrong turn
- Player disconnected

--------------------------------------------------

### Game End:

```json
{
   "type": "game_over",
   "state": { ... },
   "winner": 1
}
```

- Sent when all boxes are filled
- Includes final state and winner

--------------------------------------------------

## 7. Academic Integrity & References

Code Origin:
The socket communication structure was adapted from the course TCP Echo Server example. The game logic, protocol design, and synchronization mechanisms were implemented by the group.

--------------------------------------------------

GenAI Usage:
- ChatGPT was used to help design the JSON protocol and README formatting
- Claude was used to come up with ideas for limitations
- GenAI (Claude AI) was used to create the Graphical User Interface in gui.py

--------------------------------------------------

References:
- Python Socket Programming HOWTO
- Real Python: Introduction to Python Threading
- TA Guided Tutorial https://www.youtube.com/playlist?list=PL-8C2cUhmkO1yWLTCiqf4mFXId73phvdx
- Claude AI

--------------------------------------------------
