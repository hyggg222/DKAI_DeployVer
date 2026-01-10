# Contributing to DK_AI System

Thank you for your interest in contributing to the DK_AI Vehicle Entry/Exit Management System!

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, hardware)
- Error messages or logs

### Suggesting Enhancements

We welcome feature requests! Please open an issue with:
- Clear description of the feature
- Use case and benefits
- Possible implementation approach (if you have ideas)

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Write clear, commented code
   - Follow existing code style
   - Test your changes thoroughly

4. **Commit your changes**
   ```bash
   git commit -m "Add feature: description"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**
   - Provide clear description of changes
   - Reference any related issues
   - Include screenshots if UI changes

## 📋 Development Guidelines

### Code Style

- **Python**: Follow PEP 8 guidelines
- **Dart/Flutter**: Follow official Dart style guide
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and small

### Testing

- Test your changes with both test server and production server
- Verify mobile app functionality if backend changes affect it
- Test on different hardware if possible

### Commit Messages

Use clear and descriptive commit messages:
- `feat: add license plate confidence threshold`
- `fix: resolve camera connection timeout issue`
- `docs: update installation instructions`
- `refactor: optimize frame processing logic`

## 🏗️ Project Structure

Before contributing, familiarize yourself with:
- `ai_server.py` - Main production server
- `ai_server_test.py` - Test server with video files
- `src/` - Core AI processing modules
- `mobile_flutter/` - Flutter mobile application

## 🔍 Areas for Contribution

We especially welcome contributions in:
- Performance optimizations
- Additional camera support
- Mobile app UI/UX improvements
- Documentation improvements
- Bug fixes
- Test coverage

## 📧 Questions?

Feel free to open an issue for any questions about contributing!

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
