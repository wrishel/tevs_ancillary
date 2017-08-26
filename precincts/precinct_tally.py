class Onceonly:
	def __init__(self):
		self.donelist = set()

	def do_once(self, list):
		"""Do each item in list unless it has been done before"""
		for item in list:
			if item not in donelist:
				self.process(item)

	def process(self, item):
		"""abstract method must be overriden in instance"""
		raise NotImplementedError

class tallyonce(Onceonly):
	def process(self, item):
		