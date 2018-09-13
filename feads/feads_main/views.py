from django.shortcuts import render
from django.shortcuts import redirect
from .models import DataScienceResource
from .models import Decisions
from django.contrib.auth.decorators import login_required
from collections import Counter


@login_required
def index(request, title, err_msg=""):
    '''View for jury decisions on the :obj:`DataScienceResource`
    defined by :obj:`title`'''
    # Get the DataScienceResource and Decisions data
    dsr = DataScienceResource.objects.get(title=title)
    decisions = Decisions.objects.filter(resource=dsr,
                                         user=request.user).first()
    # Develop the context dependent on previous decision feedback
    context = {"dsr": dsr, "allowed": True, "err_msg": err_msg}
    # If not decision has been found, it implies that the user is
    # a valid django user, but has not been assigned to this task
    if decisions is None:
        context["err_msg"] = "You are not on the jury for this decision."
        context["allowed"] = False
    # The user has been assigned to this task, so retrieve previous data
    else:
        context["previous_choice"] = decisions.decision
        context["previous_comment"] = decisions.comment
        decision_field = Decisions._meta.get_field('comment')
        # If the task is no longer active then say so
        if not dsr.active:
            context["err_msg"] = "This issue has been closed."
        # Otherwise work out whether this user has provided previous feedback
        elif decisions.comment != decision_field.default:
            context["err_msg"] = ("Thank you for participating. "
                                  "You can continue to amend your feedback "
                                  "until the resource has been approved.")
    # Done
    return render(request, 'feads_main/index.html', context=context)


@login_required
def process_decision(request, title):
    '''Processes the POST request from jury decision invoked in
    :obj:`index`, by updating the relevant :obj:`Decisions` object
    (and inadvertently updating the :obj:`DataScienceResource` via
    the :obj:`Decisions.save` method)
    '''
    # Get the POST data (the user's decision and comment)
    _choice = request.POST.get('decision', '') == "approve"
    comment = request.POST.get('comment', '')
    # If the DataScienceResource is no longer active then say so
    dsr = DataScienceResource.objects.get(title=title)
    if not dsr.active:
        return redirect("index", title=title)
    # Check whether the feedback is long enough to defer
    if (not _choice) and len(comment) < 30:
        return index(request, title,
                     ("In order to defer you must provide "
                      "at least 30 characters of feedback!"))
    # Update the :obj:`Decisions` object
    decisions = Decisions.objects.filter(resource=dsr,
                                         user=request.user).first()
    decisions.comment = comment
    decisions.decision = _choice
    decisions.save()
    return redirect("index", title=title)


def active_resources(request):
    '''Generate information for the summary table'''
    # The following field is for identifying pending feedback
    decision_field = Decisions._meta.get_field('comment')
    # Generate one row per DataScienceResource
    dsr_list = []
    for dsr in DataScienceResource.objects.all():
        n = 0  # Total number of decisions (including pending)
        approvals, comments = [], []
        for decision in Decisions.objects.filter(resource=dsr):
            n += 1
            # If the decision is pending
            if decision.comment == decision_field.default:
                continue
            approvals.append(decision.decision)
            comments.append(decision.comment)
        # Generate counts of approvals and deferrals
        counts = Counter(approvals)
        # Append the row data. Note that decision counts are presented
        # as percentages
        dsr_list.append((dsr, "{:3.0f}".format(100*counts[True]/n),
                         "{:3.0f}".format(100*counts[False]/n),
                         comments))
    # Done
    context = {"dsr_list": dsr_list}
    return render(request, 'feads_main/active_resources.html', context=context)
