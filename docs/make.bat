@ECHO OFF
REM Windows command file for Sphinx documentation

pushd %~dp0

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=.
set BUILDDIR=_build

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found.
	echo.Install with: pip install -r requirements-docs.txt
	exit /b 1
)

popd
