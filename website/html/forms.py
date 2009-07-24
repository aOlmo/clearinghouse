"""
<Program Name>
  accounts/forms.py

<Started>
  October, 2008

<Author>
  ivan@cs.washington.edu
  Ivan Beschastnikh

<Purpose>

<Usage>
  For more information on forms in django see:
  http://docs.djangoproject.com/en/dev/topics/forms/
"""

from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
import django.forms as forms



class GeniUserCreationForm(DjangoUserCreationForm):
  affiliation = forms.CharField(min_length=2, max_length=64, error_messages={'required': 'Enter an Affiliation'})
  pubkey = forms.FileField(label="My Public Key", required=False)
  gen_upload_choice = forms.ChoiceField(label="", choices=((1, 'Generate key pairs for me'), (2, 'Let me upload my public key')))

  def __init__(self, *args):
    DjangoUserCreationForm.__init__(self, *args)
    self.fields['password1'].error_messages['required'] = 'Enter a password'
    self.fields['password2'].error_messages['required'] = 'Verify your password'
    self.fields['username'].error_messages['required'] = 'Enter a username'
  
  def clean_password1(self):
    value = self.cleaned_data['password1']
    if len(value) < 5:
      raise forms.ValidationError, "Password must be at least 5 characters long"
    return value        

  def clean_username(self):
    value = self.cleaned_data['username']
    if len(value) < 3:
      raise forms.ValidationError, "Usernames must be at least 3 characters long"
    if len(value) > 32:
      raise forms.ValidationError, "Usernames must be at most 32 characters long"
    return value

