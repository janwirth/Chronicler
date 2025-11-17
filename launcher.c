#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <libgen.h>
#include <string.h>
#include <mach-o/dyld.h>
#include <spawn.h>
#include <sys/wait.h>

extern char **environ;

int main(int argc, char *argv[]) {
    // Get the path to the executable
    char path[1024];
    uint32_t size = sizeof(path);
    if (_NSGetExecutablePath(path, &size) != 0) {
        fprintf(stderr, "Buffer too small; need size %u\n", size);
        return 1;
    }

    // Get directory of executable
    char dir_buffer[1024];
    strncpy(dir_buffer, path, sizeof(dir_buffer) - 1);
    char *dir = dirname(dir_buffer);

    // Build paths
    char python_path[2048];
    char script_path[2048];
    char venv_path[2048];

    // Use our bundled Python binary instead of symlinked one
    snprintf(python_path, sizeof(python_path), "%s/ChroniclerPython", dir);
    snprintf(script_path, sizeof(script_path), "%s/chronicler.py", dir);
    snprintf(venv_path, sizeof(venv_path), "%s/../Resources/venv", dir);

    // Set environment for Python to find venv packages
    char pythonpath[4096];
    snprintf(pythonpath, sizeof(pythonpath), "%s/lib/python3.14/site-packages", venv_path);
    setenv("VIRTUAL_ENV", venv_path, 1);
    setenv("PYTHONPATH", pythonpath, 1);

    // Change to the MacOS directory
    chdir(dir);

    // Build argv array for Python
    char *new_argv[] = {
        python_path,
        script_path,
        NULL
    };

    // Use posix_spawn to launch Python, which properly connects to window server
    pid_t pid;
    int status;

    status = posix_spawn(&pid, python_path, NULL, NULL, new_argv, environ);

    if (status == 0) {
        // Wait for child process
        if (waitpid(pid, &status, 0) != -1) {
            return WEXITSTATUS(status);
        } else {
            perror("waitpid failed");
            return 1;
        }
    } else {
        fprintf(stderr, "posix_spawn failed: %s\n", strerror(status));
        return 1;
    }
}
