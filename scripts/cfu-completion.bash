# Bash completion for cfu (CommandLineFu CLI)
# Source this file or add to /etc/bash_completion.d/

_cfu_completions() {
    local cur prev words cword
    _init_completion || return

    local commands="search top tagged random"
    local tags="awk sed grep ssh git curl tar find bash network disk process text file system docker systemd"

    case "${prev}" in
        cfu)
            COMPREPLY=($(compgen -W "${commands} -i -n --interactive --limit --no-color --help" -- "${cur}"))
            return
            ;;
        search|s|find)
            # No completion for search query
            return
            ;;
        tagged|tag|t)
            COMPREPLY=($(compgen -W "${tags}" -- "${cur}"))
            return
            ;;
        top|best|popular)
            COMPREPLY=($(compgen -W "5 10 20 50" -- "${cur}"))
            return
            ;;
        -n|--limit)
            COMPREPLY=($(compgen -W "5 10 20 50 100" -- "${cur}"))
            return
            ;;
    esac

    # Handle subcommand completion
    if [[ ${cword} -eq 1 ]]; then
        COMPREPLY=($(compgen -W "${commands} -i --interactive" -- "${cur}"))
    fi
}

complete -F _cfu_completions cfu
