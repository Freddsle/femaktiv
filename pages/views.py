from django.http import Http404
from django.shortcuts import render

from .content import examples


def home(request):
    data = examples()
    return render(
        request,
        "pages/home.html",
        {"examples": data["conversations"], "questions": data["questions"][:3]},
    )


def community(request):
    data = examples()
    topic = request.GET.get("topic", "")
    if topic not in {item["slug"] for item in data["topics"]}:
        topic = ""
    questions = [item for item in data["questions"] if not topic or item["topic"] == topic]
    return render(
        request,
        "pages/community.html",
        {"topics": data["topics"], "questions": questions, "selected_topic": topic},
    )


def question(request, slug):
    data = examples()
    item = next((item for item in data["questions"] if item["slug"] == slug), None)
    if item is None:
        raise Http404
    return render(request, "pages/question.html", {"question": item})


def example(request, slug):
    item = next((item for item in examples()["conversations"] if item["slug"] == slug), None)
    if item is None:
        raise Http404
    return render(request, "pages/example.html", {"example": item})
