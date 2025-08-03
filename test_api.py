import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("Testing Notes App API")
    print("=" * 50)
    
    # Test registration
    print("\n1. Testing User Registration")
    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    response = requests.post(f"{BASE_URL}/register", json=register_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test login
    print("\n2. Testing User Login")
    login_data = {
        "username": "testuser",
        "password": "testpassword123"
    }
    
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    print(f"Status: {response.status_code}")
    login_response = response.json()
    print(f"Response: {login_response}")
    
    if response.status_code == 200:
        token = login_response["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test creating a note
        print("\n3. Testing Create Note")
        note_data = {
            "title": "My First Note",
            "content": "This is the content of my first note."
        }
        
        response = requests.post(f"{BASE_URL}/notes", json=note_data, headers=headers)
        print(f"Status: {response.status_code}")
        create_response = response.json()
        print(f"Response: {create_response}")
        
        if response.status_code == 201:
            note_id = create_response["id"]
            
            # Test getting all notes
            print("\n4. Testing Get All Notes")
            response = requests.get(f"{BASE_URL}/notes", headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            # Test getting specific note
            print(f"\n5. Testing Get Note {note_id}")
            response = requests.get(f"{BASE_URL}/notes/{note_id}", headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            # Test updating note
            print(f"\n6. Testing Update Note {note_id}")
            update_data = {
                "title": "Updated Note Title",
                "content": "This is the updated content."
            }
            
            response = requests.put(f"{BASE_URL}/notes/{note_id}", json=update_data, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            # Test deleting note
            print(f"\n7. Testing Delete Note {note_id}")
            response = requests.delete(f"{BASE_URL}/notes/{note_id}", headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")

if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"Error: {e}")

