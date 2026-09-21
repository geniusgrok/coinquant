import unittest
from research.nonlinear_memory import predict

class MemoryTests(unittest.TestCase):
    def test_unmatured_labels_and_future_perturbations_cannot_change_prediction(self):
        observations=[(10,[1,0,0,0],.2),(20,[1,1,1,1],-.3),(30,[1,0,0,0],999)]
        self.assertEqual(predict(observations,20,[1,0,0,0]),(.2,2))
        observations[-1]=(30,[1,-100,-100,-100],-999)
        self.assertEqual(predict(observations,20,[1,0,0,0]),(.2,2))
        self.assertEqual(predict(observations,9,[1,0,0,0]),(0,0))
