class AiRulesGenerator < Formula
  include Language::Python::Virtualenv

  desc "CLI tool that generates comprehensive AI coding agent rules"
  homepage "https://github.com/rpupo63/ai-rules-generator"
  url "https://github.com/rpupo63/ai-rules-generator/archive/v1.0.0.tar.gz"
  sha256 "0019dfc4b32d63c1392aa264aed2253c1e0c2fb09216f8e2cc269bbfb8bb49b5"
  license "MIT"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"ai-rules-generator", "--help"
    system bin/"ai-rules", "--help"
  end

  def post_install
    puts <<~EOS
      AI Rules Generator installed successfully!

      To get started:
        1. Run: ai-rules-generator init
           This will set up your AI provider and API keys interactively.
           All settings are stored in ~/.config/ai-rules-generator/config.json
           No need to modify your shell configuration!

        2. Navigate to your project directory

        3. Run: ai-rules-generator project-init
           This will generate AI rules for your project

      Optional AI providers can be installed separately:
        pip3 install openai anthropic

      For more information, visit: https://github.com/rpupo63/ai-rules-generator
    EOS
  end
end
