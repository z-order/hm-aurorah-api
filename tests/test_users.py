"""
Test user endpoints
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    """Test user creation"""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpassword123",
        "is_active": True,
        "is_superuser": False,
    }

    response = await client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_get_users(client: AsyncClient):
    """Test getting all users"""
    # Create a user first
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpassword123",
        "is_active": True,
        "is_superuser": False,
    }
    await client.post("/api/v1/users/", json=user_data)

    # Get all users
    response = await client.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient):
    """Test getting user by ID"""
    # Create a user first
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpassword123",
        "is_active": True,
        "is_superuser": False,
    }
    create_response = await client.post("/api/v1/users/", json=user_data)
    user_id = create_response.json()["id"]

    # Get user by ID
    response = await client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == user_data["email"]


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient):
    """Test updating user"""
    # Create a user first
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpassword123",
        "is_active": True,
        "is_superuser": False,
    }
    create_response = await client.post("/api/v1/users/", json=user_data)
    user_id = create_response.json()["id"]

    # Update user
    update_data = {"full_name": "Updated Test User"}
    response = await client.put(f"/api/v1/users/{user_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == update_data["full_name"]


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient):
    """Test deleting user"""
    # Create a user first
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpassword123",
        "is_active": True,
        "is_superuser": False,
    }
    create_response = await client.post("/api/v1/users/", json=user_data)
    user_id = create_response.json()["id"]

    # Delete user
    response = await client.delete(f"/api/v1/users/{user_id}")
    assert response.status_code == 204

    # Verify user is deleted
    get_response = await client.get(f"/api/v1/users/{user_id}")
    assert get_response.status_code == 404
