{
 "cells": [
  {
   "attachments": {},
   "cell_type": "markdown",
   "id": "617e9085",
   "metadata": {},
   "source": [
    "# Sample code to test the API running the Python program"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "636a7234",
   "metadata": {},
   "outputs": [],
   "source": [
    "import openai\n",
    " \n",
    "openai.api_type = \"azure\"\n",
    "openai.api_key = \"...\"\n",
    "openai.api_base =  \"https://api.hku.hk\"\n",
    "openai.api_version = \"2024-06-01\"\n",
    " \n",
    "# create a completion\n",
    "# engine= gpt-35-turbo | gpt-4 | gpt-4-32k | gpt-4o |\n",
    "completion = openai.ChatCompletion.create(engine=\"gpt-35-turbo\", messages=[{\"role\": \"user\", \"content\": \"Hello world!\"}])\n",
    " \n",
    "# print the completion\n",
    "print(completion.choices[0].message.content)\n",
    "#print(completion)\n"
   ]
  },
  {
   "attachments": {},
   "cell_type": "markdown",
   "id": "138f59fe",
   "metadata": {},
   "source": [
    "# AttributeError: module 'openai' has no attribute 'ChatCompletion'\n",
    "If you find this error, you may try the following steps to solve it.\n",
    "\n",
    "Step 1: Upgrade openai to >= 0.27\n",
    "````\n",
    "pip install --upgrade openai\n",
    "````\n",
    "Step 2: Restart the application that you are running the Jupyter notebook"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.11.3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
