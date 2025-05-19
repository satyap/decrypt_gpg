
use strict;
use warnings;
use Time::HiRes qw(time);

my $dec='decrypted';
my $base=$ARGV[0] || 'documents';
my $pass='';#$ARGV[0] || '';

if($pass eq '') {
    print "GPG password: ";
    system('stty','-echo');
    $pass = <STDIN>;
    system('stty','echo');
    print "\n";
    chomp($pass);
}

`mkdir $dec`;
$|=1;

my $t1 = time();
recurse($base);
my $elapsed = time() - $t1;
print("took $elapsed seconds");

sub recurse() {
    my $dir=shift;
    opendir(DIR,$dir);
    my @files=readdir DIR;
    closedir DIR;
    `mkdir -p $dec/$dir`;
    print "$dir";

    my @childs = ();

    my @dirs = ();
    foreach my $file(sort @files) {
        next if substr($file,0,1) eq '.';
        my $fullname="$dir/$file";
        if(-d $fullname) {
            push @dirs, $fullname;
            next;
        }
        my $targetdir="$dec/$dir";
        # is a file
        #my $pid = fork;
        #die "cannot fork" unless defined $pid;
        #if($pid==0) {
            if($file=~/gpg$/) {
                my $newfile=$file;
                $newfile=~s/.gpg$//;
                # Quietly decrypt with given passphrase
                print `gpg --ignore-mdc-error --batch -qd --passphrase $pass $fullname > $targetdir/$newfile`;
                if($? != 0) {
                    print "$fullname\n";
                    die;
                }
                $file=$newfile;
            } else {
                print `cp $fullname $targetdir/$file`;
            }
            if($file=~/.tgz$/) {
                print `cd $targetdir && tar xzf $file`;
                print `rm $targetdir/$file`;
            }
            if($file=~/\.gz$/) {
                print `cd $targetdir && gunzip -f $file`;
                $file=~s/.gz$//;
            }
            if($file=~/.tar$/) {
                print `cd $targetdir && tar xf $file`;
                print `rm $targetdir/$file`;
            }
            print ".";
            #   exit;
            #}
            #push @childs, $pid;
    }
    foreach (@childs) {
        my $tmp = waitpid($_, 0);
    }
    foreach my $d(@dirs) {
        print "\n";
        recurse($d);
    }
}

print "\n";

