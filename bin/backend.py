import json
import motor.motor_tornado
import multiprocessing as mp
import pymongo



class Backend():
	def __init__(self):
		pass

	def initialize(self):
		pass

	async def workflow_query(self, page, page_size):
		raise NotImplementedError()

	async def workflow_create(self, workflow):
		raise NotImplementedError()

	async def workflow_get(self, id):
		raise NotImplementedError()

	async def workflow_update(self, id, workflow):
		raise NotImplementedError()

	async def workflow_delete(self, id):
		raise NotImplementedError()

	async def task_query(self, page, page_size):
		raise NotImplementedError()

	async def task_create(self, task):
		raise NotImplementedError()

	async def task_get(self, id):
		raise NotImplementedError()



class JSONBackend(Backend):
	def __init__(self, url):
		self._lock = mp.Lock()
		self._url = url
		self.initialize()

	def initialize(self, error_not_found=False):
		# load database from json file
		try:
			self._db = json.load(open(self._url))

		# initialize empty database if json file doesn't exist
		except FileNotFoundError:
			self._db = {
				"workflows": [],
				"tasks": []
			}
			self.save()

	def load(self):
		self._db = json.load(open(self._url))

	def save(self):
		json.dump(self._db, open(self._url, "w"))

	async def workflow_query(self, page, page_size):
		self._lock.acquire()
		self.load()

		# sort workflows by date_created in descending order
		self._db["workflows"].sort(key=lambda w: w["date_created"], reverse=True)

		# return the specified page of workflows
		workflows = self._db["workflows"][(page * page_size) : ((page + 1) * page_size)]

		self._lock.release()

		return workflows

	async def workflow_create(self, workflow):
		self._lock.acquire()
		self.load()

		# append workflow to list of workflows
		self._db["workflows"].append(workflow)

		self.save()
		self._lock.release()

	async def workflow_get(self, id):
		self._lock.acquire()
		self.load()

		# search for workflow by id
		workflow = None

		for w in self._db["workflows"]:
			if w["_id"] == id:
				workflow = w
				break

		self._lock.release()

		# return workflow or raise error if workflow wasn't found
		if workflow != None:
			return workflow
		else:
			raise IndexError("Workflow was not found")

	async def workflow_update(self, id, workflow):
		self._lock.acquire()
		self.load()

		# search for workflow by id and update it
		found = False

		for i, w in enumerate(self._db["workflows"]):
			if w["_id"] == id:
				# update workflow
				self._db["workflows"][i] = workflow
				found = True
				break

		self.save()
		self._lock.release()

		# raise error if workflow wasn't found
		if not found:
			raise IndexError("Workflow was not found")

	async def workflow_delete(self, id):
		self._lock.acquire()
		self.load()

		# search for workflow by id and delete it
		found = False

		for i, w in enumerate(self._db["workflows"]):
			if w["_id"] == id:
				# delete workflow
				self._db["workflows"].pop(i)
				found = True
				break

		self.save()
		self._lock.release()

		# raise error if workflow wasn't found
		if not found:
			raise IndexError("Workflow was not found")

	async def task_query(self, page, page_size):
		self._lock.acquire()
		self.load()

		# sort tasks by date_created in descending order
		self._db["tasks"].sort(key=lambda t: t["utcTime"], reverse=True)

		# return the specified page of workflows
		tasks = self._db["tasks"][(page * page_size) : ((page + 1) * page_size)]

		self._lock.release()

		return tasks

	async def task_create(self, task):
		self._lock.acquire()
		self.load()

		# append workflow to list of workflows
		self._db["tasks"].append(task)

		self.save()
		self._lock.release()

	async def task_get(self, id):
		self._lock.acquire()
		self.load()

		# search for task by id
		task = None

		for t in self._db["tasks"]:
			if t["_id"] == id:
				task = t
				break

		self._lock.release()

		# raise error if task wasn't found
		if task != None:
			return task
		else:
			raise IndexError("Task was not found")



class MongoBackend(Backend):
	def __init__(self, url):
		self._url = url
		self.initialize()

	def initialize(self):
		self._client = motor.motor_tornado.MotorClient(self._url)
		self._db = self._client["nextflow_api"]

	async def workflow_query(self, page, page_size):
		return await self._db.workflows \
			.find() \
			.sort("date_created", pymongo.DESCENDING) \
			.skip(page * page_size) \
			.to_list(length=page_size)

	async def workflow_create(self, workflow):
		return await self._db.workflows.insert_one(workflow)

	async def workflow_get(self, id):
		return await self._db.workflows.find_one({ "_id": id })

	async def workflow_update(self, id, workflow):
		return await self._db.workflows.replace_one({ "_id": id }, workflow)

	async def workflow_delete(self, id):
		return await self._db.workflows.delete_one({ "_id": id })

	async def task_query(self, page, page_size):
		return await self._db.tasks \
			.find({}, { "_id": 1, "runName": 1, "utcTime": 1, "event": 1 }) \
			.sort("utcTime", pymongo.DESCENDING) \
			.skip(page * page_size) \
			.to_list(length=page_size)

	async def task_create(self, task):
		return await self._db.tasks.insert_one(task)

	async def task_get(self, id):
		return await self._db.tasks.find_one({ "_id": id })