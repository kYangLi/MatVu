from pathlib import Path

import pytest

from matvu import find_structures, render_batch
from matvu.cli import main
from matvu.style import Style

DATA = Path(__file__).resolve().parents[1] / "examples" / "structures"
TINY = dict(width_in=1.2, dpi=60, supersample=1)


def _make_tree(root: Path) -> None:
    """A DeepH-style project: dft/<material>/.../POSCAR."""
    (root / "dft" / "A").mkdir(parents=True)
    (root / "dft" / "B" / "relax").mkdir(parents=True)
    for target in (root / "dft" / "A" / "POSCAR", root / "dft" / "B" / "relax" / "POSCAR"):
        target.write_bytes((DATA / "water.POSCAR").read_bytes())
    (root / "dft" / "notes.txt").write_text("not a structure")


def test_find_structures_recursive(tmp_path):
    _make_tree(tmp_path)
    files = find_structures([tmp_path / "dft"])
    assert len(files) == 2
    assert all(path.name == "POSCAR" for path in files)
    assert files == sorted(files)


def test_find_structures_accepts_globs_and_patterns(tmp_path):
    _make_tree(tmp_path)
    globbed = find_structures([str(tmp_path / "dft" / "**" / "POSCAR")])
    assert len(globbed) == 2
    text = find_structures([tmp_path / "dft"], patterns=["*.txt"])
    assert text == [tmp_path / "dft" / "notes.txt"]


def test_find_structures_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_structures([tmp_path / "nope"])


def test_render_batch_writes_beside_input(tmp_path):
    _make_tree(tmp_path)
    results = render_batch([tmp_path / "dft"], style=Style(**TINY))
    assert [result.ok for result in results] == [True, True]
    for result in results:
        output = result.source.with_name("POSCAR_view.png")
        assert result.outputs == [output]
        assert output.exists()
        assert result.formula == "H2O"


def test_render_batch_mirrors_tree_under_output_dir(tmp_path):
    _make_tree(tmp_path)
    results = render_batch([tmp_path / "dft"], tmp_path / "figs", style=Style(**TINY))
    expected = [
        tmp_path / "figs" / "A" / "POSCAR_view.png",
        tmp_path / "figs" / "B" / "relax" / "POSCAR_view.png",
    ]
    assert sorted(result.outputs[0] for result in results) == sorted(expected)
    assert all(path.exists() for path in expected)


def test_render_batch_multiple_formats(tmp_path):
    _make_tree(tmp_path)
    results = render_batch(
        [tmp_path / "dft" / "A"], formats=["png", "pdf"], style=Style(**TINY)
    )
    outputs = results[0].outputs
    assert {path.suffix for path in outputs} == {".png", ".pdf"}
    assert all(path.exists() for path in outputs)


def test_render_batch_skip_existing(tmp_path):
    _make_tree(tmp_path)
    render_batch([tmp_path / "dft"], style=Style(**TINY))
    results = render_batch([tmp_path / "dft"], style=Style(**TINY), skip_existing=True)
    assert all(result.skipped for result in results)


def test_render_batch_collects_errors(tmp_path):
    _make_tree(tmp_path)
    (tmp_path / "dft" / "C").mkdir()
    (tmp_path / "dft" / "C" / "POSCAR").write_text("not a structure")
    results = render_batch([tmp_path / "dft"], style=Style(**TINY))
    failures = [result for result in results if not result.ok]
    assert len(failures) == 1
    assert "ValueError" in failures[0].error


def test_render_batch_parallel_jobs(tmp_path):
    _make_tree(tmp_path)
    results = render_batch([tmp_path / "dft"], style=Style(**TINY), jobs=2)
    assert len(results) == 2
    assert all(result.ok for result in results)
    assert all(result.outputs[0].exists() for result in results)


def test_batch_cli(tmp_path, capsys):
    _make_tree(tmp_path)
    code = main(
        [
            "batch",
            str(tmp_path / "dft"),
            "--width",
            "1.2",
            "--dpi",
            "60",
            "--supersample",
            "1",
        ]
    )
    assert code == 0
    assert (tmp_path / "dft" / "A" / "POSCAR_view.png").exists()
    assert "2 rendered" in capsys.readouterr().out
