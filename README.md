# CMPT371_A3_DotsAndBoxes
Assignment 3
Course: CMPT 371 - Data Communications & Networking  
Instructor: Mirza Zaeem Baig  
Semester: Spring 2026  

--------------------------------------------------

Group Members
Name                   Student ID     Email
Edan Stasiuk           30xxxxxxx      jane.doe@university.edu
Noah Vattathichirayil  301548329      nva16@sfu.ca

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

--------------------------------------------------

## 2. System Limitations & Edge Cases

TBD

--------------------------------------------------

TBD

--------------------------------------------------

TBD

--------------------------------------------------

TBD

--------------------------------------------------

## 3. Video Demo

Our 2-minute video demonstration covering connection establishment, data exchange, real-time gameplay, and game completion can be viewed below:

Watch Project Demo on YouTube

--------------------------------------------------

## 4. Prerequisites (Fresh Environment)

To run this project, you need:

- Python 3.10 or higher
- No external pip installations required (uses socket, threading, json, sys)
- (Optional) VS Code or Terminal

RUBRIC NOTE: No external libraries are required.

--------------------------------------------------

## 5. Step-by-Step Run Guide

**RUBRIC NOTE:** The grader must be able to copy-paste these commands.

---

### Step 1: Start the Server

Open your terminal and navigate to the project folder. The server binds to 127.0.0.1 on port 5050.

```bash
python server.py
# Console output: "[STARTING] Server is listening on 127.0.0.1:5050"
```

---

### Step 2: Connect Player 1

Open a new terminal window (keep the server running). Run the client script to start the first client.

```bash
python client.py
# Console output: "Connected. Waiting for opponent..."
```

---

### Step 3: Connect Player 2

Open a third terminal window. Run the client script again to start the second client.

```bash
python client.py
# Console output: "Connected. Waiting for opponent..."
# Console output: "Match found! You are Player 2."
```

---

### Step 4: Gameplay

1. Players take turns drawing lines between adjacent dots.

2. When prompted, enter your move in the format:
   ```
   row col direction
   ```

3. Where:
   - `row`, `col` specify the starting dot  
   - `direction` is:
     - `H` for horizontal  
     - `V` for vertical  

4. The server will:
   - Update the board on both clients  
   - Check for completed boxes  
   - Update scores  

5. If a player completes a box:
   - They earn a point  
   - They get another turn  

6. The game ends when all boxes are completed, and the winner is announced.

--------------------------------------------------

## 6. Technical Protocol Details (JSON over TCP)

Message Format:
{"type": "<string>", "payload": <data>}

--------------------------------------------------

Handshake Phase:

Client sends:
{"type": "CONNECT"}

Server responds:
{"type": "WELCOME", "payload": "Player 1"}

--------------------------------------------------

Gameplay Phase:

Client sends:
{"type": "MOVE", "row": 1, "col": 1, "direction": "H"}

Server broadcasts:
{
  "type": "UPDATE",
  "board": {...},
  "scores": {"P1": 2, "P2": 1},
  "turn": "Player 2",
  "status": "ongoing"
}

--------------------------------------------------

Game End:

{
  "type": "GAME_OVER",
  "winner": "Player 1"
}

--------------------------------------------------

## 7. Academic Integrity & References

RUBRIC NOTE: List all references used and assistance received.

Code Origin:
The socket communication structure was adapted from the course TCP Echo Server example. The game logic, protocol design, and synchronization mechanisms were implemented by the group.

--------------------------------------------------

GenAI Usage:
- ChatGPT was used to help design the JSON protocol and README formatting

--------------------------------------------------

References:
- Python Socket Programming HOWTO
- Real Python: Introduction to Python Threading
- TA Guided Tutorial https://www.youtube.com/playlist?list=PL-8C2cUhmkO1yWLTCiqf4mFXId73phvdx

--------------------------------------------------
