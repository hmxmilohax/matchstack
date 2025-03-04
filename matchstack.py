#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
import tempfile
import sys

# Determine the directory where the script is located.
exec_dir = os.path.dirname(os.path.abspath(__file__))

# Set arsonc_path based on the operating system.
if sys.platform.startswith("win"):
    arsonc_path = os.path.join(exec_dir, "arsonc.exe")
else:
    arsonc_path = os.path.join(exec_dir, "arsonc")

# =======================
# ANSI Color Definitions
# =======================
COLORS = {
    "red":      '\033[91m',   # For operators and similar tokens.
    "green":    '\033[92m',   # For function names in definitions.
    "blue":     '\033[94m',   # For control keywords and borders.
    "yellow":   '\033[93m',   # For string literals.
    "magenta":  '\033[95m',   # For numbers.
    "cyan":     '\033[96m',   # For variables.
    "white":    '\033[97m',   # For built-in functions and constants.
    "light_green": '\033[92m',  # Previously "white", now used for built-in functions/constants
    "light_blue":    '\033[94m',   # For built-in functions and constants.
    "gray":     '\033[90m',   # For comments.
    "orange":   '\033[38;5;208m',  # For file names.
    "purple":   '\033[35m',   # For DSL keywords (class names, property names, etc.)
    "reset":    '\033[0m'
}

# Aliases for clarity:
FILE_COLOR           = COLORS["orange"]
STRING_COLOR         = COLORS["yellow"]
NUMBER_COLOR         = COLORS["magenta"]
VARIABLE_COLOR       = COLORS["cyan"]
GLOBAL_VAR_COLOR     = COLORS["cyan"]
CONTROL_COLOR        = COLORS["blue"]
BUILTIN_COLOR        = COLORS["light_green"]
OPERATOR_COLOR       = COLORS["red"]
CONSTANT_COLOR       = COLORS["light_blue"]
COMMENT_COLOR        = COLORS["gray"]
DSL_COLOR            = COLORS["purple"]  # New: for DSL keywords.
FUNC_DEF_KEY_COLOR   = COLORS["blue"]
FUNC_DEF_NAME_COLOR  = COLORS["green"]

# =======================
# Token Group Definitions
# =======================
# (The token lists remain unchanged; see original code for full content.)
CONTROL_KEYWORDS = [
    "and", "as", "block", "case", "cond", "else", "for", "foreach_active_player",
    "foreach_screen", "from", "goto_screen", "if", "if_else", "initially", "let", "loop",
    "named", "never", "new", "not", "or", "pop_screen", "prog", "return", "return-from",
    "script_task", "set",  # 'set' is a core assignment operator.
    "shiftf", "switch", "then", "to", "trace", "typecase", "typep",
    "while", "with", "with-accessors", "with-condition-restarts", "with-compilation-unit",
    "with-input-from-string", "with-open-file", "with-open-stream", "with-output-to-string",
    "with-package-iterator", "with-simple-restart", "with-slots", "with-standard-io-syntax",
    "y-or-n-p", "yes-or-no-p"
]
BUILTIN_FUNCTIONS = [
    "abort", "abs", "acosh", "acos", "ctypcase", "delete", "dolist", "dotimes",
    "etypecase", "exists", "export", "get_symbol", "is_modifier_active", "mapc",
    "mapcar", "mapcan", "mapcon", "mapl", "maplist", "object", "prog\\*", "push_screen", "set_data",  "set_var",
    "set-exclusive-or", "set-dispatch-macro-character", "set-macro-character", "set-pprint-dispatch",
    "set-syntax-from-char", "shiftf", "type-error-datum", "type-error-expected-type", "type-of",
    "ui", "wild-pathname-p", "warn", "write", "write-byte", "write-char", "write-string", "write-to-string",
    "two-way-stream-input-stream", "two-way-stream-output-stream", "truncate", "truename", "tree-equal",
    "translate-logical-pathname", "translate-pathname", "to-alter", "time", "terpri", "terminate-producing",
    "tanh", "tan", "tailp", "third", "synonym-stream-symbol", "symbol-function", "symbol-name", "symbol-package",
    "symbol-plist", "symbol-value", "symbolp", "sxhash", "svref", "summing", "sum", "substitute", "substitute-if",
    "substitute-if-not", "subst", "subst-if", "subst-if-not", "subsetp", "subseries", "subseq", "sublis",
    "string", "string-capitalize", "string-char-p", "string-downcase", "string-equal", "string-greaterp",
    "string-lessp", "string-left-trim", "string-not-equal", "string-not-greaterp", "string-not-lessp", "stringp",
    "string-right-trim", "string-trim", "string-upcase", "string>", "string>=", "string=", "string<", "string<=",
    "string/=", "streamp", "stream-element-type", "stream-error-stream", "stream-external-format", "split",
    "split-if", "special-form-p", "sort", "some", "software-type", "software-version", "slot-boundp",
    "slot-exists-p", "slot-makunbound", "slot-missing", "slot-unbound", "slot-value", "sleep", "sixth",
    "sinh", "sin", "simple-bit-vector-p", "simple-condition-format-arguments", "simple-condition-format-string",
    "simple-string-p", "simple-vector-p", "signum", "signal", "short-site-name", "shared-initialize", "shadow",
    "shadowing-import", "seventh", "setq", "setf", "set-difference", "set-char-bit", "series", "second", "search",
    "schar", "scan", "scan-alist", "scan-file", "scan-fn", "scan-fn-inclusive", "scan-hash", "scan-lists-of-lists",
    "scan-lists-of-lists-fringe", "scan-multiple", "scan-plist", "scan-range", "scan-symbols", "scan-sublists",
    "sbit", "scale-float", "rplaca", "rplacd", "row-major-aref", "round", "rotatef", "room", "reverse",
    "revappend", "result-of", "restart-bind", "restart-case", "restart-name", "rest", "require",
    "replace", "rename-file", "rename-package", "remf", "remhash", "remprop", "remove", "remove-duplicates",
    "remove-method", "reinitialize-instance", "reduce", "realp", "realpart", "read", "read-byte", "read-char",
    "read-char-no-hang", "read-delimited-list", "read-from-string", "read-line", "read-preserving-whitespace",
    "readtable-case", "readtablep", "rational", "rationalize", "rationalp", "rassoc", "rassoc-if", "rassoc-if-not",
    "random", "random-state-p", "quote", "push", "pushnew", "psetf", "psetq", "provide", "proclaim", "prog1",
    "prog2", "progn", "producing", "probe-file", "print", "print-object", "print-unreadable-object", "prin1",
    "previous", "pprint-dispatch", "pprint-exit-if-list-exhausted", "pprint-fill", "pprint-indent",
    "pprint-linear", "pprint-logical-block", "pprint-newline", "pprint-pop", "pprint-tab", "pprint-tabular",
    "positions", "position", "position-if", "position-if-not", "pop", "plusp", "phase", "peek-char", "pathname",
    "pathname-device", "pathname-directory", "pathname-host", "pathname-match-p", "pathname-name", "pathnamep",
    "pathname-type", "pathname-version", "parse-integer", "parse-macro", "parse-namestring", "pairlis",
    "package-error-package", "package-name", "package-nicknames", "package-shadowing-symbols", "package-used-by-list",
    "package-use-list", "packagep", "output-stream-p", "open", "open-stream-p", "oddp", "nunion", "numerator",
    "numberp", "nth", "nth-value", "nthcdr", "nsubstitute", "nsubstitute-if", "nsubstitute-if-not", "nsubst",
    "nsubst-if", "nsubst-if-not", "nsublis", "nstring-capitalize", "nstring-downcase", "nstring-upcase",
    "nset-difference", "nset-exclusive-or", "nreconc", "nreverse", "nintersection", "next-in", "next-method-p",
    "next-out", "ninth", "nconc", "nconcing", "nbutlast", "namestring", "name-char", "multiple-value-bind",
    "multiple-value-list", "multiple-value-setq", "muffle-warning", "mismatch", "minimize", "minimizing",
    "minusp", "mingle", "method-combination-error", "method-qualifiers", "merge-pathnames", "member", "member-if",
    "member-if-not", "memberp", "maximize", "maximizing", "mask", "mask-field", "mapping", "map", "map-fn",
    "map-into", "maphash", "makunbound", "make-array", "make-echo-stream", "make-dispatch-macro-character",
    "make-condition", "make-concatenated-stream", "make-char", "make-broadcast-stream", "make-hash-table",
    "make-instance", "make-instances-obsolete", "make-list", "make-load-form", "make-load-form-saving-slots",
    "make-package", "make-pathname", "make-random-state", "make-sequence", "make-string", "make-string-input-stream",
    "make-string-output-stream", "make-synonym-stream", "make-two-way-stream", "machine-instance", "machine-type",
    "machine-version", "macroexpand", "macroexpand-1", "macro-function", "long-site-name", "loop-finish",
    "lower-case-p", "ldiff", "ldb", "ldb-test", "lcm", "latch", "last", "lambda", "keywordp", "iterate", "isqrt",
    "invoke-debugger", "invoke-restart", "invalid-method-error", "intersection", "intern", "interactive-stream-p",
    "integer-decode-float", "integer-length", "integerp", "int-char", "inspect", "input-stream-p",
    "initialize-instance", "in-package", "import", "imagpart", "ignore-errors", "identity", "host-namestring",
    "hash-table-count", "hash-table-p", "hash-table-rehash-size", "hash-table-rehash-threshold",
    "hash-table-size", "hash-table-test", "handler-case", "handler-bind", "graphic-char-p", "get",
    "get-decoded-time", "get-internal-real-time", "get-internal-run-time", "get-output-stream-string",
    "get-properties", "get-setf-method", "get-setf-method-multiple-value", "getf", "gethash", "gentemp",
    "gensym", "generic-function", "generator", "gcd", "gatherer", "gathering", "function-information",
    "function-keywords", "function-lambda-expression", "functionp", "funcall", "fourth", "formatter", "format",
    "floor", "float", "float-digits", "float-precision", "float-radix", "float-sign", "floatp", "first",
    "finish-output", "find", "find-all-symbols", "find-class", "find-if", "find-if-not", "find-method",
    "find-package", "find-restart", "find-symbol", "fill", "fill-pointer", "file-author", "file-error-pathname",
    "file-length", "file-namestring", "file-position", "file-string-length", "file-write-date", "fifth", "ffloor",
    "fdefinition", "fboundp", "f", "expt", "export", "expand", "exp", "every", "evenp", "eval", "evalhook",
    "error", "ensure-generic-function", "enough-namestring", "endp", "encode-universal-time", "enclose",
    "encapsulated", "elt", "eighth", "ed", "echo-stream-input-stream", "echo-stream-output-stream", "ecase",
    "dribble", "dpb", "documentation", "do-all-symbols", "do-external-symbols", "do-symbols", "destructuring-bind",
    "describe", "describe-object", "deposit-field", "denominator", "delete-file", "delete-if", "delete-if-not",
    "delete-package", "delete-duplicates"
]
OPERATOR_TOKENS = [
    "+", "-", "*", "/", "==", "!=", ">=", "<=", ">", "<", "&&", "||", "!", "mod", "rem", "incf", "decf",
    "logand", "logior", "logxor", "lognor", "logeqv", "kDataUnhandled",
    "SCROLL_SELECT_MSG",  "beatmatch",
    "SongSelectPanel", "MultiSelectListPanel", "BandScreen", "GHScreen", "UIScreen", "GamePanel",
    "OvershellPanel", "BandStorePanel", "MainHubPanel", "profile_mgr", "UILabel", "UIButton", "UIPanel",
    "Mesh", "Mat", "Group", "Tex", "GHPanel", "game", "UIComponent", "BandList", "UISlider", "memcardmgr", "song_provider",
    "gamemode", "gamecfg", "modifier_mgr", "set_localized_text",
    "include", "else", "define", "merge", "ifdef", "ifndef", "endif",
    "FOCUS_MSG", "UI_CHANGED_MSG", "TRANSITION_COMPLETE_MSG", "SELECT_DONE_MSG",
    "BUTTON_DOWN_MSG", "SCROLL_MSG", "ui", "SELECT_START_MSG", "SELECT_MSG", "BUTTON_UP_MSG",
    "single-float-negative-epsilon", "single-float-epsilon", "short-float-negative-epsilon", "short-float-epsilon",
    "pi", "nil",
    "multiple-values-limit", "most-positive-single-float", "most-positive-short-float", "most-positive-long-float",
    "most-positive-fixnum", "most-positive-double-float", "most-negative-single-float", "most-negative-short-float",
    "max", "min", "set_localized", "add_sink", "selected_sym", "set_state", "set_mode", "text_token", "color",
    "set_local_scale", "set_local_pos", "set_local_rot", "set_local_scale_index", "set_local_pos_index",
    "set_local_rot_index", "set_bitmap", "set_text", "set_type", "set_showing",
    "printf", "sprintf", "sprint", "func", "elem", "elem_var", "foreach", "foreach_int",
    "set_selected",
    "mod", "symbol", "int", "localize", "strneq", "print", "time", "random_int", "random_float",
    "random_elem", "notify", "fail", "insert_elems", "insert_elem", "size", "remove_elem",
    "resize", "aray", "set_elem", "literal", "eval", "reverse_interp", "interp", "run", "handle",
    "exit", "enter", "find", "file_exists", "find_exists", "find_elem", "find_obj", "basename",
    "has_substr", "search_replace", "push_back", "var", "pack_color", "unpack_color", "set_this",
    "macro_elem", "merge_dirs", "eq", "neq", "eql", "invalid", "equalp", "equal", "set_selected"
]
MACRO_CONSTANTS = [
    "FALSE", "TRUE",
    "kPlatformNone", "kPlatformPS2", "kPlatformXBox", "kPlatformPC", "kPlatformPS3",
    "kOldGfx", "kNewGfx",
    "kMergeMerge", "kMergeReplace", "kMergeKeep",
    "kNoInline", "kAlwaysInline", "kPrecacheInline",
    "kCopyDeep", "kCopyShallow", "kCopyFromMax", "kCopyProxy",
    "kTaskSeconds", "kTaskBeats", "kTaskUISeconds", "kTaskTutorialSeconds", "TASK_UNITS",
    "kSquareAspect", "kRegularAspect", "kWidescreenAspect",
    "kAnimRange", "kAnimLoop", "kAnimShuttle", "ANIM_ENUM",
    "k30_fps", "k480_fpb", "k30_fps_ui", "k1_fpb", "RATE_ENUM",
    "PI", "kHugeFloat",
    "kFirstFit", "kBestFit", "kLRUFit", "kLastFit",
    "kPad_L2", "kPad_R2", "kPad_L1", "kPad_R1", "kPad_Tri", "kPad_Circle", "kPad_X", "kPad_Square", "kPad_Select",
    "kPad_L3", "kPad_R3", "kPad_Start", "kPad_DUp", "kPad_DRight", "kPad_DDown", "kPad_DLeft",
    "kPad_LStickUp", "kPad_LStickRight", "kPad_LStickDown", "kPad_LStickLeft",
    "kPad_RStickUp", "kPad_RStickRight", "kPad_RStickDown", "kPad_RStickLeft", "kPad_NumButtons",
    "kLeftAnalog", "kRightAnalog",
    "kJoypadNone", "kJoypadDigital", "kJoypadAnalog", "kJoypadDualShock", "kJoypadMidi", "kJoypadXboxGuitar",
    "KB_ENTER", "KB_BACKSPACE", "KB_TAB", "KB_SPACE", "KB_a", "KB_b", "KB_c", "KB_d", "KB_e", "KB_f", "KB_g", "KB_h",
    "KB_i", "KB_j", "KB_k", "KB_l", "KB_m", "KB_n", "KB_o", "KB_p", "KB_q", "KB_r", "KB_s", "KB_t", "KB_u",
    "KB_v", "KB_w", "KB_x", "KB_y", "KB_z", "KB_CAP_LOCK", "KB_NUM_LOCK", "KB_SCROLL_LOCK", "KB_PRINT", "KB_PAUSE",
    "KB_ESCAPE", "KB_INSERT", "KB_DELETE", "KB_HOME", "KB_END", "KB_PAGE_UP", "KB_PAGE_DOWN", "KB_LEFT",
    "KB_RIGHT", "KB_UP", "KB_DOWN", "KB_F1", "KB_F2", "KB_F3", "KB_F4", "KB_F5", "KB_F6", "KB_F7", "KB_F8",
    "KB_F9", "KB_F10", "KB_F11", "KB_F12",
    "kMCNoError", "kMCNoCard", "kMCNotFormatted", "kMCDifferentCard", "kMCReadWriteFailed", "kMCCorrupt",
    "kMCNotEnoughSpace", "kMCGeneralError", "kMCFileExists", "kMCAlreadyFormatted", "kMCDamaged",
    "kMCNoDeviceFound", "kMCFileNotFound", "kMCMultipleFilesFound",
    "k1KHz", "k2KHz", "k4KHz", "k10KHz", "k20KHz",
    "kFXModeOff", "kFXModeRoom", "kFXModeSmallStudio", "kFXModeMedStudio", "kFXModeLargeStudio",
    "kFXModeHall", "kFXModeSpace", "kFXModeEcho", "kFXModeDelay", "kFXModePipe",
    "kFXCoreNone", "kFXCore0", "kFXCore1",
    "kAttackLinear", "kAttackExp", "kSustainLinInc", "kSustainLinDec", "kSustainExpInc", "kSustainExpDec",
    "kReleaseLinear", "kReleaseExp",
    "kVolumeEmpty", "kVolumeTriangles", "kVolumeBSP", "kVolumeBox",
    "kMutableVerts", "kMutableFaces", "kMutableEdges", "kMutableAll",
    "kConstraintNone", "kConstraintLocalRotate", "kConstraintParentWorld", "kConstraintLookAtTarget",
    "kConstraintShadowTarget", "kConstraintBillboardZ", "kConstraintBillboardXZ", "kConstraintBillboardXYZ",
    "kConstraintFastBillboardXYZ",
    "COPY_DEFAULT", "COPY_LITKEYS", "COPY_MATKEYS", "COPY_MESHGEOM", "COPY_SHARETRANS", "COPY_MESHKEYS",
    "COPY_PARTKEYS", "COPY_TRANSKEYS", "COPY_CHILDREN", "COPY_PARTS", "COPY_CAMKEYS", "COPY_ENVKEYS", "COPY_BASEONLY",
    "kLeft", "kCenter", "kRight", "kTop", "kMiddle", "kBottom",
    "kTopLeft", "kTopCenter", "kTopRight", "kMiddleLeft", "kMiddleCenter", "kMiddleRight", "kBottomLeft",
    "kBottomCenter", "kBottomRight",
    "kTexRegular", "kTexRendered", "kTexMovie", "kTexBackBuffer", "kTexFrontBuffer", "kTexRenderedNoZ",
    "kLightPoint", "kLightDirectional", "kLightFakeSpot", "kLightFloorSpot",
    "kBlendDest", "kBlendSrc", "kBlendAdd", "kBlendSrcAlpha", "kBlendSrcAlphaAdd", "kBlendSubtract", "kBlendMultiply",
    "BLEND_ENUM",
    "kZModeDisable", "kZModeNormal", "kZModeTransparent", "kZModeForce", "kZModeDecal", "ZMODE_ENUM",
    "kStencilIgnore", "kStencilWrite", "kStencilTest", "STENCILMODE_ENUM",
    "kTexWrapClamp", "kTexWrapRepeat", "TEXWRAP_ENUM",
    "kTexGenNone", "kTexGenXfm", "kTexGenSphere", "kTexGenProjected", "kTexGenXfmOrigin", "kTexGenEnviron",
    "TEXGEN_ENUM",
    "kRecordRegular", "kRecordCreated", "kRecordDeleted",
    "kUnreliable", "kReliable", "kLocal", "kHost", "kJoin", "kLost", "kWon", "kRestart", "kInLobby", "kLoading", "kInGame",
    "JOIN_RESPONSE_MSG", "REMOVE_PLAYER_MSG", "INVITE_ACCEPTED_MSG", "BUTTON_DOWN_MSG", "BUTTON_UP_MSG",
    "JOYPAD_CONNECT_MSG", "KEY_MSG", "SELECT_MSG", "SELECT_START_MSG", "FOCUS_MSG", "SCREEN_CHANGE_MSG",
    "TRANSITION_COMPLETE_MSG", "TEXT_ENTRY_MSG", "TEXT_ENTRY_INVALID_MSG", "SCROLL_MSG",
    "kComponentNormal", "kComponentFocused", "kComponentDisabled", "kComponentSelecting",
    "kExcitementBoot", "kExcitementBad", "kExcitementOkay", "kExcitementGreat", "kExcitementPeak", "kNumExcitements",
    "kPlayNow", "kPlayNoBlend", "kPlayFirst", "kPlayLast", "kPlayDirty", "kPlayNoLoop", "kPlayLoop",
    "kPlayGraphLoop", "kPlayNodeLoop", "kPlayRealTime", "kPlayUserTime", "kPlayBeatAlign1", "kPlayBeatAlign2",
    "kPlayBeatAlign4", "kPlayBeatAlign8", "kPlayNoDefault", "kPlayBeatTime", "PLAY_BLEND_FLAGS", "PLAY_LOOP_FLAGS",
    "PLAY_TIME_FLAGS",
    "kRotNone", "kRotFull", "kRotX", "kRotY", "kRotZ",
    "kCollidePlane", "kCollideSphere", "kCollideInsideSphere", "kCollideCylinder", "kCollideInsideCylinder",
    "kFaceFxLipSyncRotX", "kFaceFxLipSyncRotY", "kFaceFxLipSyncRotZ", "FACE_FX_LIP_SYNC_OPS",
    "kDbSilence",
    "STD_EXTS", "PS2_EXTS", "XBOX_EXTS", "STD_SKIP_DIRS", "SYSTEM_SUBDIRS", "SYSTEM_DIRS", "XBOX_HD_EXTS",
    "kTriggerNone", "kTriggerShow", "kTriggerHide", "kTriggerEnable", "kTriggerDisable",
    "SYSTEMWORLDEVENTS", "WORLDEVENTS", "SYSTEMUIEVENTS", "UIEVENTS", "HIDE_IN_PROXY", "LANGUAGES",
    "kGemTypeNormal", "kGemTypeDoubler", "kGemTypeCatcher", "kPlayer1", "kPlayer2", "kPlayerNone", "kPlayerShared"
]
DSL_KEYWORDS = [
    "Anim", "Poll", "PropAnim", "AnimFilter", "Blur", "Cam", "CamAnim", "TexRenderer", "Cursor",
    "Draw", "Environ", "EnvAnim", "Flare", "Font", "Generator", "Group", "Light", "LightAnim", "Line",
    "Mat", "MatAnim", "Mesh", "MeshAnim", "Morph", "Movie", "MultiMesh", "ParticleSys", "ParticleSysAnim",
    "ScreenMask", "RndDir", "PostProc", "Tex", "CubeTex", "Set", "Text", "Trans", "TransAnim", "TransArray",
    "MeshDeform", "PanelDir", "UIPanel", "UIScreen", "UIComponent", "UIButton", "UILabel", "UIList",
    "UIPicture", "UIProxy", "UISlider", "UITrigger", "Screenshot",
    "description", "allowed_dirs", "editor", "views", "types", "ext", "superclasses", "init", "resource_file",
    "class", "list", "help", "script", "indent", "array", "struct", "read_only", "hide", "refresh", "range"
]

# =======================
# Utility Functions
# =======================
def separate_comment(line):
    """
    Splits a line into code and comment parts.
    The first semicolon not inside a double-quoted string marks the start of a comment.
    """
    in_string = False
    for i, char in enumerate(line):
        if char == '"' and (i == 0 or line[i-1] != '\\'):
            in_string = not in_string
        if char == ';' and not in_string:
            return line[:i], line[i:]
    return line, ''

def highlight_line(line):
    """
    Applies syntax highlighting to a given line while ensuring:
    - Filenames are highlighted as a whole (e.g., `overdrive_plane.mesh`).
    - No nested re-highlighting occurs.
    """
    code, comment = separate_comment(line)

    # Strip any existing ANSI escape sequences to avoid interference with our highlighting.
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    code = ansi_escape.sub('', code)

    # Order matters here: apply patterns **from most specific to most general**.

    # 2. Highlight floating point numbers, but not whole numbers.
    def float_highlight(m):
        return f'{NUMBER_COLOR}{m.group(1)}{COLORS["reset"]}'
    
    code = re.sub(r'(?<!\d)(\d+\.\d+)(?!\w)', float_highlight, code)

    # 2.1 Highlight whole (integer) numbers.
    def int_highlight(m):
        return f'{NUMBER_COLOR}{m.group(0)}{COLORS["reset"]}'

    code = re.sub(r'\b\d+\b', int_highlight, code)

    # 3. Highlight function definitions.
    def func_def_sub(m):
        return f"{FUNC_DEF_KEY_COLOR}{m.group(1)}{COLORS['reset']} {FUNC_DEF_NAME_COLOR}{m.group(2)}{COLORS['reset']}"
    
    code = re.sub(r'\b(?i:(defun|defmacro|defmethod))\b\s+([\w\-!?<>]+)', func_def_sub, code)

    # 1. Highlight filenames as a whole (preventing partial highlighting).
    def file_highlight(m):
        return f'{FILE_COLOR}{m.group(0)}{COLORS["reset"]}'
    
    code = re.sub(r'\b[\w\-/]+\.[a-zA-Z0-9]+\b', file_highlight, code)


    # 4. Highlight strings.
    code = re.sub(r'("([^"\\]*(\\.[^"\\]*)*)")',
                  lambda m: f'{STRING_COLOR}{m.group(1)}{COLORS["reset"]}', code)

    # 5. Highlight variables starting with `$`
    code = re.sub(r'(?<![a-zA-Z0-9_])(\$[a-zA-Z0-9_]+)(?![a-zA-Z0-9_])',
                  lambda m: f'{VARIABLE_COLOR}{m.group(1)}{COLORS["reset"]}', code)

    # 6. Highlight control keywords.
    pattern_control = r'\b(' + '|'.join(CONTROL_KEYWORDS) + r')\b'
    code = re.sub(pattern_control,
                  lambda m: f'{CONTROL_COLOR}{m.group(1)}{COLORS["reset"]}', code, flags=re.IGNORECASE)

    # 7. Highlight built-in functions.
    pattern_builtin = r'\b(' + '|'.join(BUILTIN_FUNCTIONS) + r')\b'
    code = re.sub(pattern_builtin,
                  lambda m: f'{BUILTIN_COLOR}{m.group(1)}{COLORS["reset"]}', code, flags=re.IGNORECASE)

    # 8. Highlight macro constants.
    pattern_macros = r'\b(' + '|'.join(MACRO_CONSTANTS) + r')\b'
    code = re.sub(pattern_macros,
                  lambda m: f'{CONSTANT_COLOR}{m.group(1)}{COLORS["reset"]}', code, flags=re.IGNORECASE)

    # 9. Highlight operators and similar tokens.
    operator_pattern = r'(?<![\w])(' + '|'.join(map(re.escape, OPERATOR_TOKENS)) + r')(?![\w])'
    code = re.sub(operator_pattern,
                  lambda m: f'{OPERATOR_COLOR}{m.group(0)}{COLORS["reset"]}', code, flags=re.IGNORECASE)

    # 10. Highlight constants (nil, t).
    code = re.sub(r'\b(nil|t)\b',
                  lambda m: f'{CONSTANT_COLOR}{m.group(1)}{COLORS["reset"]}', code, flags=re.IGNORECASE)

    # Apply comment highlighting last so it isn't affected by other regex replacements.
    if comment:
        comment = f'{COMMENT_COLOR}{comment}{COLORS["reset"]}'

    return code + comment


def process_line(line):
    """
    Processes a single line by searching for a block comment that contains an ID.
    Returns a tuple (extracted_id, cleaned_line).
    """
    match = re.search(r'/\*.*?ID:\s*(\d+).*?\*/', line)
    if match:
        id_int = int(match.group(1))
        cleaned_line = re.sub(r'/\*.*?ID:\s*\d+.*?\*/', '', line)
    else:
        id_int = None
        cleaned_line = line
    # Remove extra whitespace after a starting brace.
    cleaned_line = re.sub(r'\{\s+', '{', cleaned_line)
    return id_int, cleaned_line.rstrip("\n")

def pretty_print_snippet(lines, target_index, start_idx, end_idx, dta_filename, target_id):
    header = f"Snippet from {dta_filename} (target id: {target_id})"
    border = "+" + "-" * (len(header) + 4) + "+"
    print(COLORS["blue"] + border + COLORS["reset"])
    print(f"|  {COLORS['blue']}{header}{COLORS['reset']}  |")
    print(COLORS["blue"] + border + COLORS["reset"])

    output_lines = []
    i = start_idx

    while i < end_idx:
        original_line = lines[i]
        extracted_id, cleaned_line = process_line(original_line)
        line_is_target = (i == target_index)

        # Check if the line is only an open brace.
        if cleaned_line.strip() == "{":
            if (i + 1) < end_idx:
                next_line = lines[i + 1]
                extracted_id2, cleaned_line2 = process_line(next_line)
                next_line_is_target = ((i + 1) == target_index)

                # "ID-only" means there's an extracted ID on that line, but nothing else.
                if extracted_id2 is not None and cleaned_line2.strip() == "":
                    merged_is_target = (line_is_target or next_line_is_target)
                    marker = "==>" if merged_is_target else "   "
                    marker_print = f"{COLORS['red']}{marker}{COLORS['reset']}" if merged_is_target else marker

                    # Preserve the exact indentation of the "{" line.
                    if "{" in original_line:
                        leading_indent = original_line[:original_line.find("{")]
                    else:
                        leading_indent = ""
                    # Note: the id-only line's indent is dropped.
                    brace_highlighted = leading_indent + highlight_line("{")
                    # Use a 4-character alignment for the ID.
                    id_field = f"{COLORS['green']}{extracted_id2:>4}:{COLORS['reset']}"
                    # Build the merged line.
                    merged_line = f"{marker_print}{id_field}{brace_highlighted}"
                    output_lines.append(merged_line)
                    i += 2  # Skip the open brace and the ID-only line.

                    # Now check if the following line (if any) is a single token (e.g. "if").
                    if i < end_idx:
                        extra_original = lines[i]
                        extra_extracted, extra_cleaned = process_line(extra_original)
                        # Consider it "single token" if there's no ID and exactly one word.
                        if extra_extracted is None and extra_cleaned.strip() != "":
                            tokens = extra_cleaned.strip().split()
                            if len(tokens) == 1:
                                # Append this extra token (highlighted) directly to the merged line.
                                extra_highlighted = highlight_line(tokens[0])
                                output_lines[-1] = output_lines[-1].rstrip("\n") + extra_highlighted
                                i += 1  # Skip that line.
                    continue  # Done merging, move on.

        # --- Normal line handling ---
        marker = "==>" if line_is_target else "   "
        marker_print = f"{COLORS['red']}{marker}{COLORS['reset']}" if line_is_target else marker
        if extracted_id is not None:
            id_field = f"{COLORS['green']}{extracted_id:>4}:{COLORS['reset']}"
        else:
            id_field = " " * 5

        highlighted_line = highlight_line(cleaned_line)
        final_line = f"{marker_print}{id_field}{highlighted_line}"
        output_lines.append(final_line)
        i += 1

    # === POST-PROCESS: remove one "indent block" (4 leading spaces) from each line ===
    new_output_lines = []
    for line in output_lines:
        # Optionally strip ANSI codes to detect real leading spaces,
        # but for simplicity let's just remove 4 spaces if they're literally at the start:
        # This regex removes exactly 4 spaces at the beginning, if present.
        #line = re.sub(r'^ {4}', '', line)
        new_output_lines.append(line)

    # Print them
    for line in new_output_lines:
        print(line)

    print(COLORS["blue"] + border + COLORS["reset"])

def main():
    parser = argparse.ArgumentParser(
        description=("Process a .dta file using arsonc compile and decompile commands, "
                     "and display a snippet around a target ID line from the final output "
                     "with enhanced syntax highlighting.")
    )
    parser.add_argument("input_file", help="Path to the input .dta file")
    parser.add_argument("target_id", type=int, help="Target ID number to search for (e.g., 227)")
    args = parser.parse_args()

    adjusted_target = args.target_id - 1

    input_path = os.path.abspath(args.input_file)
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    exec_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = tempfile.mkdtemp(dir=exec_dir)

    try:
        base_name = os.path.basename(input_path)
        temp_input_path = os.path.join(temp_dir, base_name)
        shutil.copy(input_path, temp_input_path)

        compile_cmd = [
            arsonc_path,
            "compile",
            temp_input_path,
            "--encryption", "none",
            "--output-encoding", "utf8"
        ]
        result_compile = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result_compile.returncode != 0:
            print("Error: Compile command failed.", file=sys.stderr)
            sys.exit(result_compile.returncode)

        dtb_file = os.path.splitext(base_name)[0] + ".dtb"
        dtb_path = os.path.join(temp_dir, dtb_file)
        if not os.path.exists(dtb_path):
            print(f"Error: Expected output file '{dtb_path}' not found.", file=sys.stderr)
            sys.exit(1)

        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)

        decompile_cmd = [
            arsonc_path,
            "decompile",
            "-l",
            "-i", dtb_path
        ]
        result_decompile = subprocess.run(decompile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result_decompile.returncode != 0:
            print("Error: Decompile command failed.", file=sys.stderr)
            sys.exit(result_decompile.returncode)

        final_dta_path = os.path.join(temp_dir, base_name)
        if not os.path.exists(final_dta_path):
            print(f"Error: Final .dta file '{final_dta_path}' not found.", file=sys.stderr)
            sys.exit(1)

        with open(final_dta_path, 'r') as f:
            lines = f.readlines()

        target_pattern = re.compile(r'ID:\s*' + re.escape(str(adjusted_target)) + r'\s*\*/')
        target_index = None
        for idx, line in enumerate(lines):
            if target_pattern.search(line):
                target_index = idx
                break

        if target_index is None:
            print(f"Pattern for adjusted target ID '{adjusted_target}' not found in the final .dta file.")
        else:
            start_idx = max(0, target_index - 5)
            end_idx = min(len(lines), target_index + 1 + 20)
            pretty_print_snippet(lines, target_index, start_idx, end_idx, base_name, args.target_id)

    finally:
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    main()
