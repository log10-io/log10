import random
from pydantic import BaseModel

def ground_truth(n: str) -> str:
    return str(n)

def noisy_predictor(n: str) -> str:
    n_int = int(n)
    return str(n_int + random.randint(-10, 10)) if random.randint(1, 10) <= 5 else n

def _echo_eval(ground_truth: str, prediction: str) -> int:
    return int(ground_truth) - int(prediction)

def _rating_emoji(diff: int) -> str:
    if diff == 0:
        return "✅"
    elif diff > 0:
        return f"↗️"
    else:
        return "↘"

def _verbal_rating(diff: int) -> str:
    ratings = [
        (lambda d: d == 0, "perfect"),
        (lambda d: 0 < d < 3, "good"),
        (lambda d: 3 <= d < 6, "okay"),
        (lambda d: 6 <= d < 8, "bad"),
        (lambda d: d >= 8, "terrible"),
    ]
    return next(rating for condition, rating in ratings if condition(abs(diff)))

class EchoFeedback(BaseModel):
    direction: str
    verbal_rating: str

    @staticmethod
    def create(ground_truth: str, prediction: str) -> "EchoFeedback":
        diff = _echo_eval(ground_truth, prediction)
        return EchoFeedback(direction=_rating_emoji(diff), verbal_rating=_verbal_rating(diff))
