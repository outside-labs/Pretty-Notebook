import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.fastapi import register_tortoise
from tortoise.contrib.pydantic import pydantic_model_creator

from passlib.hash import bcrypt

import jwt

from decouple import config



router = APIRouter()

JWT_SECRET = config('JWT_SECRET')
JWT_ALGO = config('JWT_ALGO')
TOKEN_LIFETIME = timedelta(days=30)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/token')
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token', auto_error=False)



class User(Model):
	""" """
	id = fields.IntField(primary_key=True)
	username = fields.CharField(max_length=50, unique=True)
	password_hash = fields.CharField(max_length=128)
	tok_uuid = fields.TextField(default=lambda: secrets.token_urlsafe(32))
	# group = fields.TextField(default='user')

	def verify_password(self, password):
		""" """
		return bcrypt.verify(password, self.password_hash)

class Password(Model):
	""" """
	password_hash = fields.CharField(max_length=128)



User_Pydantic = pydantic_model_creator(User, name='User', exclude=('password_hash', 'tok_uuid'))
UserIn_Pydantic = pydantic_model_creator(User, name='UserIn', exclude=('tok_uuid',), exclude_readonly=True)

PasswordIn_Pydantic = pydantic_model_creator(Password, name='PasswordIn', exclude_readonly=True)



async def get_optional_user(token: str = Depends(optional_oauth2_scheme)):
	""" bypassing my own HTTPException handling ->
		providing access to optional Depends 
	"""
	if token is None:
		return None

	try:
		user = await get_current_user(token)
	except HTTPException:
		user = None

	return user

@router.post('/api/users', response_model=User_Pydantic)
async def create_user(user: UserIn_Pydantic, curr_user: User_Pydantic = Depends(get_optional_user)):
	""" Create User 
	"""
	# print(curr_user)

	root_user = await User.filter(id=1)

	if root_user:
		# only allowing our init generated root user
		# without creds 
		if not curr_user:
			raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cannot access.")
		# for user creation
		if not curr_user.id == 1:
			raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not allowed.")

	user_obj = User(username=user.username, password_hash=bcrypt.hash(user.password_hash))
	await user_obj.save()
	return await User_Pydantic.from_tortoise_orm(user_obj)


async def authenticate_user(username: str, password: str):
	""" """
	user = await User.filter(username=username).first()
	if not user:
		return False
	if not user.verify_password(password=password):
		return False
	return user

async def _generate_token(user):
	now = datetime.now(timezone.utc)
	token_id = secrets.token_urlsafe(32)
	user.tok_uuid = token_id
	
	await user.save(update_fields=["tok_uuid"])

	payload = {
		"sub": str(user.id),
		"username": user.username,
		"tok_uuid": token_id,
		"iat": now,
		"exp": now + TOKEN_LIFETIME
		}

	return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)	

@router.post('/api/token')
async def generate_token(form_data: OAuth2PasswordRequestForm = Depends()):
	""" Generate Token 
	"""
	user = await authenticate_user(username=form_data.username, password=form_data.password)
	
	if not user:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username or password')
	
	token = await _generate_token(user)

	return {'access_token': token, 'token_type': 'bearer'}


def unauthorized(detail: str) -> HTTPException:
	""" """
	return HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail=detail,
		headers={"WWW-Authenticate": "Bearer"},
		)

async def get_current_user(token: str = Depends(oauth2_scheme)):
	""" """
	try:
		payload = jwt.decode(
			token,
			JWT_SECRET,
			algorithms=[JWT_ALGO],
			options={"require": ["sub", "tok_uuid", "exp"]},
			)

	except jwt.ExpiredSignatureError as exc:
		raise unauthorized("Token expired") from exc

	except jwt.InvalidTokenError as exc:
		raise unauthorized("Could not validate credentials") from exc

	try:
		user_id = int(payload["sub"])
		token_id = payload["tok_uuid"]

	except (KeyError, TypeError, ValueError) as exc:
		raise unauthorized("Could not validate credentials") from exc

	user = await User.get_or_none(id=user_id)

	if user is None or not isinstance(token_id, str):
		raise unauthorized("Could not validate credentials")

	if not secrets.compare_digest(token_id, user.tok_uuid):
		raise unauthorized("Token revoked or superseded")
	
	return await User_Pydantic.from_tortoise_orm(user) # convert to pydantic, user isnt being passed directly, token is being passed

@router.get('/api/users/me', response_model=User_Pydantic)
async def get_user(user: User_Pydantic = Depends(get_current_user)):
	""" Get User 
	"""
	return user


@router.post('/api/users/me', response_model=User_Pydantic)
async def reset_password(password: PasswordIn_Pydantic, user: User_Pydantic = Depends(get_current_user)):
	""" Reset Password 
	"""
	orm_user = await User.get_or_none(id=user.id)

	if orm_user is None:
		raise unauthorized("Could not validate credentials")
	
	orm_user.password_hash = bcrypt.hash(password.password_hash)
	orm_user.tok_uuid = secrets.token_urlsafe(32) # rotate tok_uuid too
	
	await orm_user.save(update_fields=["password_hash", "tok_uuid"])

	return await User_Pydantic.from_tortoise_orm(orm_user)



@router.get('/api')
async def api_index(user: User_Pydantic = Depends(get_current_user)):
	""" basic index, returns if authorized 
	"""
	return {"authenticated": True, "username": user.username}







