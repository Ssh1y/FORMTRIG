#include <libxml/xmlmemory.h>
#include <libxml/parser.h>
#include <libxml/xmlregexp.h>
#include <libxml/xmlstring.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char g_fail_malloc_at = 0;
static unsigned int g_malloc_count = 0;

static void *hook_malloc(size_t size) {
  g_malloc_count++;
  if (g_fail_malloc_at != 0 && g_malloc_count == g_fail_malloc_at)
    return NULL;
  return malloc(size);
}

static void hook_free(void *ptr) {
  free(ptr);
}

static void *hook_realloc(void *ptr, size_t size) {
  return realloc(ptr, size);
}

static char *hook_strdup(const char *str) {
  size_t len = strlen(str) + 1;
  char *copy = (char *)malloc(len);
  if (copy)
    memcpy(copy, str, len);
  return copy;
}

static unsigned char *read_file(const char *path, size_t *len_out) {
  FILE *f = fopen(path, "rb");
  if (!f)
    return NULL;
  if (fseek(f, 0, SEEK_END) != 0) {
    fclose(f);
    return NULL;
  }
  long len = ftell(f);
  if (len < 0) {
    fclose(f);
    return NULL;
  }
  rewind(f);
  unsigned char *buf = (unsigned char *)malloc((size_t)len + 1);
  if (!buf) {
    fclose(f);
    return NULL;
  }
  size_t got = fread(buf, 1, (size_t)len, f);
  fclose(f);
  *len_out = got;
  return buf;
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;

  size_t len = 0;
  unsigned char *buf = read_file(argv[1], &len);
  if (!buf)
    return 2;
  if (len < 2) {
    free(buf);
    return 0;
  }

  g_fail_malloc_at = buf[0];
  size_t regex_len = len - 1;
  xmlChar *regex = (xmlChar *)malloc(regex_len + 1);
  if (!regex) {
    free(buf);
    return 2;
  }
  memcpy(regex, buf + 1, regex_len);
  regex[regex_len] = 0;

  if (xmlMemSetup(hook_free, hook_malloc, hook_realloc, hook_strdup) != 0) {
    free(regex);
    free(buf);
    return 2;
  }

  xmlRegexpPtr compiled = xmlRegexpCompile(regex);
  if (compiled)
    xmlRegFreeRegexp(compiled);

  free(regex);
  free(buf);
  xmlCleanupParser();
  return 0;
}
