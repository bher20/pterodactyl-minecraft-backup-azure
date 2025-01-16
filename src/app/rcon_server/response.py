import json

class Response():
  data      = None
  error     = None
  message   = None
  status    = None

  def __init__(self, status: bool, message: str = None, error: str = None, data: map = None):
    self.status   = status
    self.message  = message
    self.error    = error
    self.data     = data


  def toJSON(self):
      return json.dumps(
          self,
          default=lambda o: o.__dict__, 
          sort_keys=True)

  def __str__(self):
    return self.toJSON()
