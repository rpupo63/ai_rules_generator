# Maintainer: Beto
pkgname=ai-rules-generator
pkgver=1.0.0
pkgrel=1
pkgdesc="A CLI tool that generates comprehensive AI coding agent rules for Cursor and Claude Code"
arch=('any')
url="https://github.com/rpupo63/ai-rules-generator"
license=('MIT')
depends=('python' 'ai-model-picker')
optdepends=(
    'python-openai: For OpenAI provider support'
    'python-anthropic: For Anthropic Claude provider support'
)
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=()
sha256sums=()

build() {
    cd "$startdir"
    python -m build --wheel --no-isolation
}

package() {
    cd "$startdir"
    python -m installer --destdir="$pkgdir" dist/*.whl

    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
