from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.fastapi import register_tortoise
from tortoise.contrib.pydantic import pydantic_model_creator

from passlib.hash import bcrypt

import jwt

JWT_SECRET = 'myjwtsecret' # <- be better.

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

async def authenticate_user(username: str, password: str):
	user = await User.get(username=username)
	if not user:
		return False
	if not user.verify_password(password=password):
		return False
	return user

@router.post('/token')
async def generate_token(form_data: OAuth2PasswordRequestForm = Depends()): # form_data depends on OAuth2PasswordRequestForm
	user = await authenticate_user(username=form_data.username, password=form_data.password)
	if not user:
		# return {'error': 'invalid credentials'}
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username or password')

	user_obj = await User_pydantic.from_tortoise_orm(user)
	token = jwt.encode(payload=user_obj.dict(), key=JWT_SECRET) # <- you don't want your password hash in the payload

	return {'access_token': token, 'token_type': 'bearer'}



class User(Model):
	id = fields.IntField(pk=True)
	username = fields.CharField(max_length=50, unique=True)
	password_hash = fields.CharField(max_length=128)

	def verify_password(self, password):
		return bcrypt.verify(password, self.password_hash)



User_pydantic = pydantic_model_creator(User, name='User')
UserIn_Pydantic = pydantic_model_creator(User, name='UserIn', exclude_readonly=True)

@router.post('/api/users', response_model=User_pydantic)
async def create_user(user: UserIn_Pydantic): # form_data depends on OAuth2PasswordRequestForm
	user_obj = User(username=user.username, password_hash=bcrypt.hash(user.password_hash))
	await user_obj.save()
	return await User_pydantic.from_tortoise_orm(user_obj)


async def get_current_user(token: str = Depends(oauth2_scheme)):
	try:
		payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256']) #<- is their default algorithm
		user = User.get(id=payload.get('id'))
	except:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username or password')

	return await User_pydantic.from_tortoise_orm(user) # convert to pydantic, user isnt being passed directly, token is being passed


@router.get('/api/users/me', response_model=User_pydantic)
async def get_user(user: User_pydantic = Depends(get_current_user)): # form_data depends on OAuth2PasswordRequestForm
	return user


@router.get('/api')
async def api_index(token: str = Depends(oauth2_scheme)):
	return {'the_token': token}


# register_tortoise(
# 	router,
# 	db_url='sqlite://db.sqlite3',
# 	modules={'models': ['auth_api']},
# 	generate_schemas=True,
# 	add_exception_handlers=True
# 	)


