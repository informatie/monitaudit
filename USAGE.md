#### Using Monitaudit in Another Application

Once your package is published to PyPI (or if you are working on it locally), you can easily import it into any other Python application. 

#### 1. Installation

#### Option A: Install from PyPI (Production)

If you have successfully published your package to PyPI, add it to your new application using your package manager: 

bash

# If using uv (Recommended)
uv add monitaudit

# If using standard pip
pip install monitaudit

#### Option B: Install Directly from GitHub (Private/Pre-release)

If you updated your repository to private but want your other server
applications to use it securely via SSH,
install it directly from the Git source tracker: 

bash

# Using uv
uv add git+ssh://git@github.com/informatie/monitaudit.git

# Using standard pip
pip install git+ssh://git@github.com/informatie/monitaudit.git

#### Option C: Editable Local Development (Testing Locally)

If you are developing your second application on the *same* Ubuntu Server and want to test changes to monitaudit in real time, install it using a local editable path: 

bash

# Step into your new application's folder, then run:
uv add --editable /home/zadmin/projects/monitaudit

#### 2. Code Implementation Example

See the examples folder repo monitaudit-examples
