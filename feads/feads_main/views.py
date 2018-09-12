from django.shortcuts import render
from django.shortcuts import redirect
from .models import DataScienceResource
from .models import Decisions
from django.contrib.auth.decorators import login_required


@login_required
def index(request, title, err_msg=""):
    dsr = DataScienceResource.objects.get(title=title)
    context = {"dsr": dsr, "allowed": True}
    decisions = Decisions.objects.filter(resource=dsr, user=request.user).first()
    if decisions is None:
        context["err_msg"] = "You are not on the jury for this decision."
        context["allowed"] = False
    else:
        context["previous_choice"] = decisions.decision
        context["previous_comment"] = decisions.comment        
        decision_field = Decisions._meta.get_field('comment')
        if decisions.comment != decision_field.default:
            context["err_msg"] = ("Thank you for participating. "
                                  "You can continue to amend your feedback "
                                  "until the resource has been approved.")
        elif not dsr.active:
            context["err_msg"] = "This issue has been closed."

    return render(request, 'feads_main/index.html', context=context)


@login_required
def process_decision(request, title):
    _choice = request.POST.get('decision', '') == "approve"
    comment = request.POST.get('comment', '')
    dsr = DataScienceResource.objects.get(title=title)
    if not dsr.active:
        return redirect("index", title=title)

    if (not _choice) and len(comment) < 30:
        return index(request, title,
                     ("In order to defer you must provide "
                      "at least 30 characters of feedback!"))
    decisions = Decisions.objects.filter(resource=dsr, user=request.user).first()
    decisions.comment = comment
    decisions.decision = _choice
    decisions.save()
    return redirect("index", title=title)


def active_resources(request):
    context = {"dsr_list" : DataScienceResource.objects.all()}
    return render(request, 'feads_main/active_resources.html', context=context)
