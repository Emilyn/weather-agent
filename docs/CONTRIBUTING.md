# Contributing to Weather AI Agent

Thank you for your interest in contributing to the Weather AI Agent! This document provides guidelines and instructions for contributing.

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Steps to reproduce the problem
- Expected behavior vs actual behavior
- Your environment (OS, Python version, etc.)
- Relevant logs or error messages

### Suggesting Features

We welcome feature suggestions! Please create an issue with:
- A clear description of the feature
- Why this feature would be useful
- Any implementation ideas you have

### Code Contributions

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/weather-agent.git
   cd weather-agent
   ```

2. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the existing code style
   - Add comments for complex logic
   - Update documentation if needed

4. **Test your changes**
   ```bash
   # Set up environment
   source venv/bin/activate
   
   # Test locally
   cd src
   python weather_agent.py
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add: brief description of your changes"
   ```

6. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📝 Code Style Guidelines

- Use Python 3.8+ features
- Follow PEP 8 style guide
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and concise
- Handle errors gracefully

## 🧪 Testing

Before submitting a PR:
- Test the agent locally with your changes
- Ensure all weather sources still work
- Verify notifications are sent correctly
- Check that error handling works as expected

## 💡 Ideas for Contributions

Here are some areas where contributions would be welcome:

### New Features
- Add more weather data sources
- Support for multiple locations/users
- Historical weather data tracking
- Weather alerts for severe conditions
- Integration with other notification services
- Support for different languages

### Improvements
- Better AI prompts for recommendations
- More sophisticated weather aggregation algorithms
- Improved error handling and retry logic
- Performance optimizations
- Better logging and debugging tools

### Documentation
- Video tutorials
- Translation to other languages
- More detailed setup guides
- Troubleshooting guides
- API documentation

## 🔍 Code Review Process

1. All PRs will be reviewed by maintainers
2. We'll provide feedback and suggestions
3. Once approved, your PR will be merged
4. Your contribution will be acknowledged in the README

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Every contribution, no matter how small, is valuable and appreciated. Thank you for helping make Weather AI Agent better!

