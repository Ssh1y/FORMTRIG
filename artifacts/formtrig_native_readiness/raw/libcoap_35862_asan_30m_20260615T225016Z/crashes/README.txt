Command line used to find this crash:

/home/cwh/FORMTRIG/experiments/aflplusplus/AFLplusplus/afl-fuzz -i /home/cwh/FORMTRIG/artifacts/rnt_corpus/LIBCOAP_CVE_2023_35862/seeds -o /tmp/formtrig_libcoap_35862_asan_30m_20260615T225016Z/selective_sweep_1800s/candidates/001_LIBCOAP_CVE_2023_35862.native_b2_keyword_len_candidate.yml -V 1800 -m none -- /tmp/formtrig_libcoap_35862_asan_30m_20260615T225016Z/libcoap_oscore_conf_replay_formtrig_selective @@

If you can't reproduce a bug outside of afl-fuzz, be sure to set the same
memory limit. The limit used for this fuzzing session was 0 B.

Need a tool to minimize test cases before investigating the crashes or sending
them to a vendor? Check out the afl-tmin that comes with the fuzzer!

Found any cool bugs in open-source tools using afl-fuzz? If yes, please post
to https://github.com/AFLplusplus/AFLplusplus/issues/286 once the issues
 are fixed :)
