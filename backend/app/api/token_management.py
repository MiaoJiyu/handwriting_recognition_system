"""
Token API for external application integration - User and School Management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..core.database import get_db
from ..models.user import User, UserRole
from ..models.school import School
from ..utils.dependencies import get_current_user, CurrentUserResponse
from ..utils.security import get_password_hash
from ..utils.datetime_utils import utc_now, serialize_datetime_utc

router = APIRouter(prefix="/v1", tags=["External Token API"])


# ============================================================================
# Pydantic Models for User Management
# ============================================================================

class CreateUserRequest(BaseModel):
    """Create user request"""
    username: str
    password: str
    nickname: Optional[str] = None
    role: str  # student, teacher, school_admin, system_admin
    school_id: Optional[int] = None


class UpdateUserRequest(BaseModel):
    """Update user request"""
    nickname: Optional[str] = None
    role: Optional[str] = None
    school_id: Optional[int] = None


class SetPasswordRequest(BaseModel):
    """Set user password request"""
    password: str


class UserResponse(BaseModel):
    """User response"""
    id: int
    username: str
    nickname: Optional[str]
    role: str
    school_id: Optional[int]
    created_at: str


# ============================================================================
# Pydantic Models for School Management
# ============================================================================

class CreateSchoolRequest(BaseModel):
    """Create school request"""
    name: str


class UpdateSchoolRequest(BaseModel):
    """Update school request"""
    name: str


class SchoolResponse(BaseModel):
    """School response"""
    id: int
    name: str
    created_at: str
    user_count: int = 0


# ============================================================================
# Helper Functions
# ============================================================================

def validate_token_permission(
    token_user: CurrentUserResponse,
    required_scope: str = "admin"
):
    """Validate if token has required permission"""
    # Get token info from the database
    # For now, we'll use the user's role as a proxy
    # In production, you'd check the actual token permissions
    
    role_priority = {
        "student": 1,
        "teacher": 2,
        "school_admin": 3,
        "system_admin": 4
    }
    
    scope_priority = {
        "read": 1,
        "write": 2,
        "admin": 3
    }
    
    # For user management, need write or admin scope
    user_priority = role_priority.get(token_user.role, 0)
    min_priority = scope_priority.get(required_scope, 1)
    
    if user_priority < min_priority:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required scope: {required_scope}"
        )


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_via_token(
    user_data: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Create a new user via Token API

    Creates a new user in the system. Permission requirements:
    - Teachers can create students
    - School admins can create students and teachers
    - System admins can create any user type

    **Permissions Required:**
    - `manage_users` permission in token
    - Or token scope must be `admin`

    **Example Request:**
    ```json
    {
      "username": "student1",
      "password": "password123",
      "nickname": "张三",
      "role": "student",
      "school_id": 1
    }
    ```

    **Example Response:**
    ```json
    {
      "id": 10,
      "username": "student1",
      "nickname": "张三",
      "role": "student",
      "school_id": 1,
      "created_at": "2026-01-31T10:00:00Z"
    }
    ```
    """
    # Validate token permissions
    validate_token_permission(current_user, "write")
    
    # Validate role
    try:
        role_enum = UserRole(user_data.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {user_data.role}. Must be one of: student, teacher, school_admin, system_admin"
        )
    
    # Permission checks based on current user role
    if current_user.role == "teacher":
        # Teachers can only create students
        if role_enum != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teachers can only create students"
            )
        # Must create in their own school
        if user_data.school_id and user_data.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only create students in your own school"
            )
    
    elif current_user.role == "school_admin":
        # School admins can create students and teachers
        if role_enum in [UserRole.SCHOOL_ADMIN, UserRole.SYSTEM_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create school admin or system admin users"
            )
        # Must create in their own school
        if user_data.school_id and user_data.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only create users in your own school"
            )
    
    elif current_user.role == "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students cannot create users"
        )
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Create user
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        nickname=user_data.nickname,
        role=role_enum,
        school_id=user_data.school_id or current_user.school_id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        nickname=new_user.nickname,
        role=new_user.role.value,
        school_id=new_user.school_id,
        created_at=serialize_datetime_utc(new_user.created_at) or serialize_datetime_utc(utc_now())
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_via_token(
    user_id: int,
    user_data: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Update user information via Token API

    Updates user information. Permission requirements:
    - Users can only update their own information
    - Teachers can update students in their school
    - School admins can update any user in their school
    - System admins can update any user

    **Permissions Required:**
    - `manage_users` permission in token
    - Or token scope must be `write` or `admin`

    **Example Request:**
    ```json
    {
      "nickname": "张三新",
      "school_id": 1
    }
    ```
    """
    # Validate token permissions
    validate_token_permission(current_user, "write")
    
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Permission checks
    if current_user.role == "student":
        # Students can only update themselves
        if target_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only update your own information"
            )
        # Cannot change role or school
        if user_data.role or user_data.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change role or school"
            )
    
    elif current_user.role == "teacher":
        # Teachers can update students in their school
        if target_user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only update students in your school"
            )
        # Cannot promote to admin roles
        if user_data.role in ["school_admin", "system_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot promote users to admin roles"
            )
    
    elif current_user.role == "school_admin":
        # School admins can update any user in their school
        if target_user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only update users in your school"
            )
        # Cannot create system admins
        if user_data.role == "system_admin" and current_user.role != "system_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create system admin users"
            )
    
    # Update fields
    if user_data.nickname is not None:
        target_user.nickname = user_data.nickname
    
    if user_data.role is not None:
        try:
            target_user.role = UserRole(user_data.role.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {user_data.role}"
            )
    
    if user_data.school_id is not None:
        target_user.school_id = user_data.school_id
    
    db.commit()
    db.refresh(target_user)
    
    return UserResponse(
        id=target_user.id,
        username=target_user.username,
        nickname=target_user.nickname,
        role=target_user.role.value,
        school_id=target_user.school_id,
        created_at=serialize_datetime_utc(target_user.created_at) or serialize_datetime_utc(utc_now())
    )


@router.post("/users/{user_id}/password")
async def set_user_password_via_token(
    user_id: int,
    password_data: SetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Set user password via Token API

    Sets a new password for a user. Permission requirements:
    - Users can only set their own password
    - Teachers can set passwords for students in their school
    - School admins can set passwords for any user in their school
    - System admins can set passwords for any user

    **Permissions Required:**
    - `manage_users` permission in token
    - Or token scope must be `write` or `admin`

    **Example Request:**
    ```json
    {
      "password": "newpassword123"
    }
    ```
    """
    # Validate token permissions
    validate_token_permission(current_user, "write")
    
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Permission checks (same as update user)
    if current_user.role == "student":
        if target_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only set your own password"
            )
    
    elif current_user.role == "teacher":
        if target_user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only set passwords for students in your school"
            )
    
    elif current_user.role == "school_admin":
        if target_user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only set passwords for users in your school"
            )
    
    # Set new password
    target_user.password_hash = get_password_hash(password_data.password)
    db.commit()
    
    return {"message": "Password updated successfully"}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_via_token(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Delete user via Token API

    Deletes a user from the system. Permission requirements match the frontend:
    - Users cannot delete themselves
    - Teachers can delete students in their school
    - School admins can delete any user in their school except other admins
    - System admins can delete any user

    **Permissions Required:**
    - `manage_users` permission in token
    - Or token scope must be `write` or `admin`

    **Note:** Deleting a user will cascade delete their samples, features, and tokens.
    """
    # Validate token permissions
    validate_token_permission(current_user, "write")
    
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot delete self
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Permission checks
    if current_user.role == "teacher":
        # Teachers can delete students in their school
        if target_user.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only delete students"
            )
        if target_user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only delete students in your school"
            )
    
    elif current_user.role == "school_admin":
        # School admins can delete any user in their school except other admins
        if target_user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only delete users in your school"
            )
        if target_user.role in [UserRole.SCHOOL_ADMIN, UserRole.SYSTEM_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete admin users"
            )
    
    elif current_user.role == "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students cannot delete users"
        )
    
    # Delete user (cascade will handle related data)
    db.delete(target_user)
    db.commit()


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_via_token(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Get user information via Token API

    Returns user information. Permission requirements:
    - Users can view their own information
    - Teachers can view students in their school
    - School admins can view any user in their school
    - System admins can view any user

    **Permissions Required:**
    - `read_users` permission in token
    - Or token scope must be `read` or higher

    **Example Response:**
    ```json
    {
      "id": 10,
      "username": "student1",
      "nickname": "张三",
      "role": "student",
      "school_id": 1,
      "created_at": "2026-01-31T10:00:00Z"
    }
    ```
    """
    # Validate token permissions
    validate_token_permission(current_user, "read")
    
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Permission checks
    if current_user.role == "student":
        if target_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only view your own information"
            )
    
    elif current_user.role == "teacher":
        if target_user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only view students in your school"
            )
    
    elif current_user.role == "school_admin":
        if target_user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only view users in your school"
            )
    
    return UserResponse(
        id=target_user.id,
        username=target_user.username,
        nickname=target_user.nickname,
        role=target_user.role.value,
        school_id=target_user.school_id,
        created_at=serialize_datetime_utc(target_user.created_at) or serialize_datetime_utc(utc_now())
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users_via_token(
    school_id: Optional[int] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    List users via Token API

    Returns a list of users. Permission requirements:
    - Students can only see themselves
    - Teachers can see students in their school
    - School admins can see all users in their school
    - System admins can see all users

    **Query Parameters:**
    - `school_id`: Filter by school ID (optional)
    - `role`: Filter by role (optional)

    **Permissions Required:**
    - `read_users` permission in token
    - Or token scope must be `read` or higher
    """
    # Validate token permissions
    validate_token_permission(current_user, "read")
    
    # Build query
    query = db.query(User)
    
    # Apply school filter
    if current_user.role == "student":
        query = query.filter(User.id == current_user.id)
    elif current_user.role == "teacher":
        query = query.filter(User.school_id == current_user.school_id)
    elif current_user.role == "school_admin":
        if school_id is None:
            query = query.filter(User.school_id == current_user.school_id)
        else:
            query = query.filter(User.school_id == school_id)
    # System admin can see all
    
    # Apply role filter
    if role:
        try:
            role_enum = UserRole(role.lower())
            query = query.filter(User.role == role_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}"
            )
    
    users = query.all()
    
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            role=user.role.value,
            school_id=user.school_id,
            created_at=user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat()
        )
        for user in users
    ]


# ============================================================================
# School Management Endpoints
# ============================================================================

@router.post("/schools", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
async def create_school_via_token(
    school_data: CreateSchoolRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Create a new school via Token API

    Creates a new school in the system.

    **Permissions Required:**
    - `manage_training` permission in token (for full admin access)
    - Or token scope must be `admin`
    - User role must be `system_admin`

    **Example Request:**
    ```json
    {
      "name": "北京大学"
    }
    ```

    **Example Response:**
    ```json
    {
      "id": 5,
      "name": "北京大学",
      "created_at": "2026-01-31T10:00:00Z",
      "user_count": 0
    }
    ```
    """
    # Validate token permissions
    validate_token_permission(current_user, "admin")
    
    # Only system admins can create schools
    if current_user.role != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can create schools"
        )
    
    # Check if school name already exists
    existing_school = db.query(School).filter(School.name == school_data.name).first()
    if existing_school:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="School name already exists"
        )
    
    # Create school
    new_school = School(name=school_data.name)
    db.add(new_school)
    db.commit()
    db.refresh(new_school)
    
    return SchoolResponse(
        id=new_school.id,
        name=new_school.name,
        created_at=new_school.created_at.isoformat() if new_school.created_at else datetime.utcnow().isoformat(),
        user_count=0
    )


@router.get("/schools", response_model=List[SchoolResponse])
async def list_schools_via_token(
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    List schools via Token API

    Returns a list of all schools.

    **Permissions Required:**
    - `read_users` permission in token
    - Or token scope must be `read` or higher

    **Example Response:**
    ```json
    [
      {
        "id": 1,
        "name": "清华大学",
        "created_at": "2026-01-01T00:00:00Z",
        "user_count": 50
      },
      {
        "id": 2,
        "name": "北京大学",
        "created_at": "2026-01-01T00:00:00Z",
        "user_count": 45
      }
    ]
    ```
    """
    # Validate token permissions
    validate_token_permission(current_user, "read")
    
    # Get all schools
    schools = db.query(School).all()
    
    result = []
    for school in schools:
        # Count users in this school
        user_count = db.query(User).filter(User.school_id == school.id).count()
        result.append(SchoolResponse(
            id=school.id,
            name=school.name,
            created_at=school.created_at.isoformat() if school.created_at else datetime.utcnow().isoformat(),
            user_count=user_count
        ))
    
    return result


@router.get("/schools/{school_id}", response_model=SchoolResponse)
async def get_school_via_token(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Get school information via Token API

    Returns school information.

    **Permissions Required:**
    - `read_users` permission in token
    - Or token scope must be `read` or higher

    **Example Response:**
    ```json
    {
      "id": 1,
      "name": "清华大学",
      "created_at": "2026-01-01T00:00:00Z",
      "user_count": 50
    }
    ```
    """
    # Validate token permissions
    validate_token_permission(current_user, "read")
    
    # Get school
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # Count users
    user_count = db.query(User).filter(User.school_id == school_id).count()
    
    return SchoolResponse(
        id=school.id,
        name=school.name,
        created_at=school.created_at.isoformat() if school.created_at else datetime.utcnow().isoformat(),
        user_count=user_count
    )


@router.put("/schools/{school_id}", response_model=SchoolResponse)
async def update_school_via_token(
    school_id: int,
    school_data: UpdateSchoolRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Update school information via Token API

    Updates school information.

    **Permissions Required:**
    - `manage_training` permission in token
    - Or token scope must be `admin`
    - User role must be `system_admin`

    **Example Request:**
    ```json
    {
      "name": "北京大学（更新）"
    }
    ```
    """
    # Validate token permissions
    validate_token_permission(current_user, "admin")
    
    # Only system admins can update schools
    if current_user.role != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can update schools"
        )
    
    # Get school
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # Check if new name is taken by another school
    if school_data.name != school.name:
        existing = db.query(School).filter(School.name == school_data.name).first()
        if existing and existing.id != school_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School name already exists"
            )
    
    # Update school
    school.name = school_data.name
    db.commit()
    db.refresh(school)
    
    # Count users
    user_count = db.query(User).filter(User.school_id == school_id).count()
    
    return SchoolResponse(
        id=school.id,
        name=school.name,
        created_at=school.created_at.isoformat() if school.created_at else datetime.utcnow().isoformat(),
        user_count=user_count
    )


@router.delete("/schools/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_school_via_token(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user)
):
    """
    Delete school via Token API

    Deletes a school from the system.

    **Permissions Required:**
    - `manage_training` permission in token
    - Or token scope must be `admin`
    - User role must be `system_admin`

    **Note:** Cannot delete a school if it has users.
    """
    # Validate token permissions
    validate_token_permission(current_user, "admin")
    
    # Only system admins can delete schools
    if current_user.role != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can delete schools"
        )
    
    # Get school
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # Check if school has users
    user_count = db.query(User).filter(User.school_id == school_id).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete school with {user_count} users. Please delete all users first."
        )
    
    # Delete school
    db.delete(school)
    db.commit()
