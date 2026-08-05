# Maintainer: Beto
pkgname=ai-rules-generator
pkgver=2.0.0
pkgrel=1
pkgdesc="Structure-only codebase context maps plus optional Cursor rules"
arch=('any')
url="https://github.com/rpupo63/ai-rules-generator"
license=('MIT')
depends=('python' 'python-tree-sitter-language-pack')
optdepends=(
    'python-networkx: PageRank ranking (in-degree fallback without it)'
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
